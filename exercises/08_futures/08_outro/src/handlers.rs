use anyhow::Ok;
use std::sync::Arc;
use tokio::io::AsyncWriteExt;
use tokio::net::TcpStream;
use tokio::sync::RwLock;

use crate::data::{Ticket, TicketDraft, TicketPatch};
use crate::helpers;
use crate::store::{TicketId, TicketStore};


pub async fn create_ticket<'a>(
    socket: &mut TcpStream,
    store: Arc<RwLock<TicketStore>>,
    buffer: &'a [u8],
    request: &mut httparse::Request<'a, 'a>,
    parse_result: Option<httparse::Status<usize>>,
) -> Result<(), anyhow::Error> {
    let body = helpers::parse_body(socket, request, buffer, parse_result).await?;
    let draft: TicketDraft = serde_json::from_str(&body)?;

    let id: TicketId = store.write().await.add_ticket(draft);
    let response = helpers::build_response(helpers::Response::Created(id)).await;

    socket.write_all(&response).await?;
    Ok(())
}

pub async fn get_ticket(
    socket: &mut TcpStream,
    store: Arc<RwLock<TicketStore>>,
    id: TicketId,
) -> Result<(), anyhow::Error> {
    let ticket: Ticket = {
        let store_guard = store.read().await;
        let ticket_lock = store_guard.get(id).unwrap();
        let ticket_guard = ticket_lock.read().ok().unwrap();
        ticket_guard.clone()
    };

    let response = helpers::build_response(helpers::Response::Ok(ticket)).await;
    socket.write_all(&response).await?;
    Ok(())
}

pub async fn update_ticket_endpoint(
    patch: TicketPatch,
    store: Arc<RwLock<TicketStore>>,
) -> Option<()> {
    let store_guard = store.write().await;
    let ticket_lock = store_guard.get(patch.id)?;
    let mut ticket_guard = ticket_lock.write().ok()?;

    if let Some(title) = patch.title {
        ticket_guard.title = title;
    }

    if let Some(description) = patch.description {
        ticket_guard.description = description;
    }

    if let Some(status) = patch.status {
        ticket_guard.status = status;
    }

    Some(())
}

pub async fn patch_ticket<'a>(
    socket: &mut TcpStream,
    store: Arc<RwLock<TicketStore>>,
    buffer: &'a [u8],
    request: &mut httparse::Request<'a, 'a>,
    parse_result: Option<httparse::Status<usize>>,
) -> Result<(), anyhow::Error> {
    let body = helpers::parse_body(socket, request, &buffer, parse_result).await?;
    let patch: TicketPatch = serde_json::from_str(&body)?;
    if let Some(()) = update_ticket_endpoint(patch, store).await {
        let response = helpers::build_response(helpers::Response::NO_CONTENT).await;
        socket.write_all(&response).await?;
    };
    Ok(())
}
