use intro_00::store::TicketStore;
use intro_00::filters;
use std::sync::Arc;
use tokio::sync::RwLock;
use warp::Filter;

#[tokio::main]
async fn main() {
    let store = Arc::new(RwLock::new(TicketStore::new()));

    let tickets_index = filters::tickets_filter(store.clone());
    let create_ticket = filters::tickets_create_filter(store.clone());
    let update_ticket = filters::tickets_update_filter(store.clone());

    // Create a route for the 404 response
    let not_found_route = warp::any()
        .map(|| warp::reply::with_status("Not Found", warp::http::StatusCode::NOT_FOUND));

    // Combine your routes
    let routes = tickets_index
        .or(create_ticket)
        .or(update_ticket)
        .or(not_found_route);

    // Start the warp server with the defined routes
    warp::serve(routes).run(([127, 0, 0, 1], 3030)).await;
}
