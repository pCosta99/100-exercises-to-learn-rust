use crate::data::{TicketDraft, TicketPatch};
use crate::store::{TicketId, TicketStore};
use std::sync::Arc;
use tokio::sync::RwLock;

// The async handler to get a ticket
pub async fn get_ticket(
    id: TicketId,
    store: Arc<RwLock<TicketStore>>,
) -> Result<impl warp::Reply, warp::Rejection> {
    // Acquire a read lock on the store
    let store_guard = store.read().await;
    // Attempt to get the ticket lock
    let ticket_lock = store_guard
        .get(id)
        .ok_or_else(|| warp::reject::not_found())?;
    // Acquire a read lock on the ticket
    let ticket_guard = ticket_lock.read().map_err(|_| warp::reject::not_found())?;
    // Clone the ticket
    let ticket = ticket_guard.clone();

    // Return the ticket as JSON
    Ok(warp::reply::json(&ticket))
}

// The async handler to create a ticket
pub async fn create_ticket(
    draft: TicketDraft,
    store: Arc<RwLock<TicketStore>>,
) -> Result<impl warp::Reply, warp::Rejection> {
    let id: TicketId = store.write().await.add_ticket(draft);

    Ok(warp::reply::with_status(
        warp::reply::json(&id),
        warp::http::StatusCode::CREATED,
    ))
}

// The async handler to create a ticket
pub async fn update_ticket(
    patch: TicketPatch,
    store: Arc<RwLock<TicketStore>>,
) -> Result<impl warp::Reply, warp::Rejection> {
    let store_guard = store.write().await;
    let ticket_lock = store_guard.get(patch.id).unwrap();
    let mut ticket_guard = ticket_lock.write().ok().unwrap();

    if let Some(title) = patch.title {
        ticket_guard.title = title;
    }

    if let Some(description) = patch.description {
        ticket_guard.description = description;
    }

    if let Some(status) = patch.status {
        ticket_guard.status = status;
    }

    Ok(warp::reply::with_status(
        "",
        warp::http::StatusCode::NO_CONTENT,
    ))
}

