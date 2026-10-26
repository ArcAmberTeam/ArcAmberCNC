//! Public process entry point for the restricted maintenance terminal.

mod commands;
mod configuration;
mod ini;
mod pa;
mod permissions;
mod targets;
mod terminal;

pub fn run() -> u8 {
    match permissions::authorize() {
        Ok(()) => pa::run(),
        Err(message) => {
            eprintln!("pa: {message}");
            77
        }
    }
}

/// Open an isolated presentation preview without account or configuration access.
/// This is a development entry point, not an authentication mode of the PA CLI.
pub fn preview() -> std::io::Result<()> {
    terminal::preview()
}

/// Fixed, argument-free root helper installed behind the maintenance sudo rule.
pub fn configuration_service() -> u8 {
    configuration::serve()
}
