fn main() {
    if let Err(error) = betterlinuxcnc_updater::run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
