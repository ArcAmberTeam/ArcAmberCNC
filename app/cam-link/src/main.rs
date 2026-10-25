#[tokio::main]
async fn main() {
    if let Err(error) = betterlinuxcnc_services::run().await {
        eprintln!("Cannot start CAM link service: {error}");
        std::process::exit(1);
    }
}
