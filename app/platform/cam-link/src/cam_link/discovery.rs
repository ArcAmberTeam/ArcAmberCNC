use super::{
    config::{duration, Options},
    protocol::{canonical_id, encode, header, json_bytes, params, Result},
};
use serde_json::{json, Value};
use std::{collections::VecDeque, net::SocketAddr};
use tokio::{
    net::UdpSocket,
    time::{interval, Instant, MissedTickBehavior},
};

pub(super) struct Discovery {
    socket: UdpSocket,
    target: SocketAddr,
    identity: Value,
    interval: std::time::Duration,
}
impl Discovery {
    pub async fn bind(options: &Options, tcp: SocketAddr, tls: bool) -> Result<Self> {
        let socket = UdpSocket::bind((
            tcp.ip(),
            options
                .discovery_bind_port
                .unwrap_or(options.discovery_port),
        ))
        .await?;
        socket.set_broadcast(true)?;
        Ok(Self {
            socket,
            target: SocketAddr::new(options.discovery_address.into(), options.discovery_port),
            interval: duration(options.discovery_interval)?,
            identity: json!({
                "version":2,"service":"bettercnc-cam-link","deviceId":options.device_id,"deviceName":options.device_name,"tcpPort":tcp.port(),"tls":tls
            }),
        })
    }
    pub async fn run(self) -> Result<()> {
        let mut ticker = interval(self.interval);
        ticker.set_missed_tick_behavior(MissedTickBehavior::Delay);
        let mut nonces = VecDeque::new();
        let mut recent = VecDeque::new();
        let mut bytes = [0; 1025];
        loop {
            tokio::select! {
                _=ticker.tick()=>{
                    let nonce=uuid::Uuid::new_v4().simple().to_string();
                    let mut packet=self.identity.clone();packet["event"]="discovery.announce".into();packet["nonce"]=nonce.clone().into();
                    nonces.push_back((nonce,Instant::now()));if nonces.len()>3{nonces.pop_front();}
                    self.socket.send_to(&encode("ANNOUNCE",&packet)?,self.target).await?;
                },
                received=self.socket.recv_from(&mut bytes)=>{
                    let (size,peer)=received?;
                    let Some(reply)=reply(&bytes[..size]) else {continue};
                    if reply["deviceId"]!=self.identity["deviceId"] || !nonces.iter().any(|(nonce,created)|reply["nonce"]==*nonce && created.elapsed()<self.interval*3){continue;}
                    while recent.front().is_some_and(|created:&Instant|created.elapsed().as_secs_f64()>=1.) {recent.pop_front();}
                    if recent.len()>=8{continue;}
                    recent.push_back(Instant::now());
                    let mut ack=self.identity.clone();ack["event"]="discovery.ack".into();ack["nonce"]=reply["nonce"].clone();ack["camId"]=reply["camId"].clone();
                    self.socket.send_to(&encode("DISCOVER_ACK",&ack)?,peer).await?;
                }
            }
        }
    }
}
fn reply(bytes: &[u8]) -> Option<Value> {
    if !(25..=1024).contains(&bytes.len()) {
        return None;
    }
    let (kind, size) = header(&bytes[..24]).ok()?;
    if kind != "DISCOVER_REPLY" || size != bytes.len() - 24 {
        return None;
    }
    let v = json_bytes(&bytes[24..]).ok()?;
    params(
        &v,
        &["version", "event", "service", "deviceId", "nonce", "camId"],
    )
    .ok()?;
    if v["version"].as_u64() != Some(2)
        || v["event"] != "discovery.reply"
        || v["service"] != "bettercnc-cam-link"
        || !["deviceId", "camId"]
            .iter()
            .all(|k| v[k].as_str().is_some_and(canonical_id))
        || !v["nonce"].as_str().is_some_and(|s| {
            s.len() == 32
                && s.bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        })
    {
        return None;
    }
    Some(v)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_malformed_and_nonreply_datagrams() {
        let v = json!({"version":2,"service":"bettercnc-cam-link","event":"discovery.reply","deviceId":uuid::Uuid::new_v4().to_string(),"camId":uuid::Uuid::new_v4().to_string(),"nonce":"a".repeat(32)});
        assert_eq!(
            reply(&encode("DISCOVER_REPLY", &v).unwrap()),
            Some(v.clone())
        );
        for (key, value) in [
            ("version", json!(true)),
            ("nonce", json!("bad")),
            ("camId", json!("bad")),
            ("token", json!("secret")),
            ("event", json!("discovery.ack")),
        ] {
            let mut bad = v.clone();
            bad[key] = value;
            assert!(reply(&encode("DISCOVER_REPLY", &bad).unwrap()).is_none());
        }
        let frame = encode("DISCOVER_REPLY", &v).unwrap();
        for bad in [
            frame[..20].to_vec(),
            [frame.clone(), vec![0]].concat(),
            vec![0; 1025],
            encode("ANNOUNCE", &v).unwrap(),
        ] {
            assert!(reply(&bad).is_none());
        }
    }
}
