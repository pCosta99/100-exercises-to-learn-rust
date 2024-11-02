// This is our last exercise. Let's go down a more unstructured path!
// Try writing an **asynchronous REST API** to expose the functionality
// of the ticket management system we built throughout the course.
// It should expose endpoints to:
//  - Create a ticket
//  - Retrieve ticket details
//  - Patch a ticket
//
// Use Rust's package registry, crates.io, to find the dependencies you need
// (if any) to build this system.

use regex::Regex;
use std::sync::Arc;
use tokio::io::AsyncReadExt;
use tokio::net::TcpStream;
use tokio::sync::RwLock;
use anyhow::anyhow;

lazy_static::lazy_static! {
    static ref TICKET_PATH_RE: Regex = Regex::new(r"^/tickets/(\d+)$").unwrap();
}

use crate::store::{TicketId, TicketStore};

pub mod data;
pub mod handlers;
pub mod helpers;
pub mod server;
pub mod store;

pub async fn handle_connection(
    mut socket: TcpStream,
    store: Arc<RwLock<TicketStore>>,
) -> Result<(), anyhow::Error> {
    let mut buffer = [0; 1024];
    match socket.read(&mut buffer).await {
        Ok(n) if n == 0 => return Ok(()), // connection closed
        Ok(_n) => {
            let mut headers = [httparse::EMPTY_HEADER; 16];
            let mut request = httparse::Request::new(&mut headers);
            let res = request.parse(&buffer).ok();
            handle_request(request, &mut socket, &buffer, store, res).await?;
        }
        Err(e) => eprintln!("Failed to read from socket; err = {:?}", e),
    }

    Ok(())
}

pub async fn handle_request<'a>(
    mut request: httparse::Request<'a, 'a>,
    socket: &mut TcpStream,
    buffer: &'a [u8],
    store: Arc<RwLock<TicketStore>>,
    parse_result: Option<httparse::Status<usize>>,
) -> Result<(), anyhow::Error> {
    match request {
        httparse::Request {
            method: Some("POST"),
            path: Some("/tickets"),
            ..
        } => handlers::create_ticket(socket, store, &buffer, &mut request, parse_result).await,
        httparse::Request {
            method: Some("PATCH"),
            path: Some(path),
            ..
        } if TICKET_PATH_RE.is_match(path) => {
            if let Some(_) = TICKET_PATH_RE.captures(path) {
                handlers::patch_ticket(socket, store, &buffer, &mut request, parse_result).await?;
            }
            Ok(())
        }
        httparse::Request {
            method: Some("GET"),
            path: Some(path),
            ..
        } if TICKET_PATH_RE.is_match(path) => {
            if let Some(caps) = TICKET_PATH_RE.captures(path) {
                let id: TicketId = caps.get(1).map(|m| m.as_str()).unwrap().parse()?;

                handlers::get_ticket(socket, store, id).await?;
            }
            Ok(())
        }
        _ => Err(anyhow!("Got something else!")),
    }
}
