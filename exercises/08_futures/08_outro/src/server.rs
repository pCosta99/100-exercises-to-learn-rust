use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::sync::RwLock;
use crate::store::TicketStore;

pub async fn init() -> Result<(TcpListener, Arc<RwLock<TicketStore>>), anyhow::Error> {
    let listener = TcpListener::bind("127.0.0.1:8080").await?;
    let store = Arc::new(RwLock::new(TicketStore::new()));
    println!("Server running on 127.0.0.1:8080");
    Ok((listener, store))
}
