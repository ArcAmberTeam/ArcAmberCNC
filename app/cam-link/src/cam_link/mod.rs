mod config;
mod control;
mod discovery;
mod feedback;
mod inbox;
mod manual;
mod protocol;
mod session;

use clap::Parser;
use std::{io::Write, sync::Arc};
use tokio::{net::TcpListener, task::JoinSet};

pub(super) async fn run() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let options = config::Options::parse();
    options.validate()?;
    let token = options.token()?;
    let tls = options.tls()?;
    let io = config::duration(options.io_timeout)?;
    let idle = config::duration(options.idle_timeout)?;
    let listener = TcpListener::bind((options.host, options.port)).await?;
    let address = listener.local_addr()?;
    let discovery = if options.discover {
        Some(discovery::Discovery::bind(&options, address, tls.is_some()).await?)
    } else {
        None
    };
    let inbox = inbox::Inbox::new(&options.inbox, options.max_bytes)?;
    let service = Arc::new(session::Service {
        options,
        token,
        inbox,
        io,
        idle,
    });
    let mut clients = JoinSet::new();
    let slots = Arc::new(tokio::sync::Semaphore::new(4));
    let mut discovery = Box::pin(async move {
        if let Some(discovery) = discovery {
            discovery.run().await
        } else {
            std::future::pending().await
        }
    });
    let mut interrupt = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::interrupt())?;
    let mut terminate = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())?;
    println!(
        "{}",
        serde_json::json!({"host":address.ip().to_string(),"port":address.port(),"inbox":service.inbox.directory})
    );
    std::io::stdout().flush()?;
    let result = loop {
        tokio::select! {
            _=interrupt.recv()=>break Ok(()),
            _=terminate.recv()=>break Ok(()),
            result=&mut discovery=>break result,
            _=clients.join_next(),if !clients.is_empty()=>{},
            connection=listener.accept()=>{
                let (stream,_)=connection?;
                let Ok(permit) = slots.clone().try_acquire_owned() else {drop(stream);continue;};
                stream.set_nodelay(true)?;
                let service=service.clone();let tls=tls.clone();
                clients.spawn(async move{
                    let _permit = permit;
                    if let Some(tls)=tls {
                        if let Ok(Ok(stream))=tokio::time::timeout(io,tls.accept(stream)).await{let _=session::run(stream,service).await;}
                    }else{let _=session::run(stream,service).await;}
                });
            }
        }
    };
    clients.shutdown().await;
    Ok(result?)
}
