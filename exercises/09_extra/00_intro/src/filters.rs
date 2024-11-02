use crate::store::{TicketId, TicketStore};
use crate::handlers;
use std::sync::Arc;
use tokio::sync::RwLock;
use warp::Filter;

// Filter to inject the store into the handler
fn with_store(
    store: Arc<RwLock<TicketStore>>,
) -> impl Filter<Extract = (Arc<RwLock<TicketStore>>,), Error = std::convert::Infallible> + Clone {
    warp::any().map(move || store.clone())
}

// GET /tickets/{id}
pub fn tickets_filter(
    store: Arc<RwLock<TicketStore>>,
) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
    warp::path!("tickets" / TicketId)
        .and(warp::get())
        .and(with_store(store.clone())) // Clone store for each request
        .and_then(handlers::get_ticket) // Asynchronously handle the ticket retrieval
        .with(warp::log("tickets::get")) // Optional: Add logging
}

// POST /tickets
pub fn tickets_create_filter(
    store: Arc<RwLock<TicketStore>>,
) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
    warp::path!("tickets")
        .and(warp::post())
        .and(warp::body::json()) // Extract the JSON body as TicketDraft
        .and(with_store(store.clone()))
        .and_then(handlers::create_ticket)
        .with(warp::log("tickets::post"))
}

// PATCH /tickets/{id}
pub fn tickets_update_filter(
    store: Arc<RwLock<TicketStore>>,
) -> impl Filter<Extract = (impl warp::Reply,), Error = warp::Rejection> + Clone {
    warp::path!("tickets" / TicketId)
        .and(warp::patch())
        .and(warp::body::json())
        .and(with_store(store.clone()))
        .map(|_id, patch, store| (patch, store))
        .and_then(|(patch, store)| handlers::update_ticket(patch, store))
        .with(warp::log("tickets::patch"))
}
