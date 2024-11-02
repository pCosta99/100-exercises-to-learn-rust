use std::sync::Arc;

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    let (listener, store) = outro_08::server::init().await?;

    loop {
        let (socket, _) = listener.accept().await?;
        tokio::spawn(outro_08::handle_connection(socket, Arc::clone(&store)));
    }
}
