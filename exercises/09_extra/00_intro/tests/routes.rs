#[cfg(test)]
mod tests {
    use intro_00::data::{TicketDraft, TicketPatch};
    use intro_00::filters;
    use intro_00::store::{TicketId, TicketStore};
    use std::sync::Arc;
    use ticket_fields::TicketTitle;
    use tokio::sync::RwLock;

    #[tokio::test]
    async fn test_create_ticket() {
        let store = Arc::new(RwLock::new(TicketStore::new()));
        let create_filter = filters::tickets_create_filter(store.clone());

        let ticket_draft = TicketDraft::new(
            "Test Ticket".to_string(),
            Some("This is a test ticket".to_string()),
        );

        let response = warp::test::request()
            .method("POST")
            .path("/tickets")
            .json(&ticket_draft)
            .reply(&create_filter)
            .await;

        assert_eq!(response.status(), warp::http::StatusCode::CREATED);
    }

    #[tokio::test]
    async fn test_get_ticket() {
        let store = Arc::new(RwLock::new(TicketStore::new()));
        let create_filter = filters::tickets_create_filter(store.clone());
        let get_filter = filters::tickets_filter(store.clone());

        // First create a ticket
        let ticket_draft = TicketDraft::new(
            "Test Ticket".to_string(),
            Some("This is a test ticket".to_string()),
        );

        warp::test::request()
            .method("POST")
            .path("/tickets")
            .json(&ticket_draft)
            .reply(&create_filter)
            .await;

        // Now get the ticket
        let response = warp::test::request()
            .method("GET")
            .path("/tickets/0") // Assuming the ticket ID starts at 0
            .reply(&get_filter)
            .await;

        assert_eq!(response.status(), warp::http::StatusCode::OK);
        // You may also want to check the response body here
    }

    #[tokio::test]
    async fn test_update_ticket() {
        let store = Arc::new(RwLock::new(TicketStore::new()));
        let create_filter = filters::tickets_create_filter(store.clone());
        let update_filter = filters::tickets_update_filter(store.clone());

        // Create a ticket first
        let ticket_draft = TicketDraft::new(
            "Test Ticket".to_string(),
            Some("This is a test ticket".to_string()),
        );

        warp::test::request()
            .method("POST")
            .path("/tickets")
            .json(&ticket_draft)
            .reply(&create_filter)
            .await;

        // Now update the ticket
        let ticket_patch = TicketPatch {
            id: TicketId(0),
            title: Some(TicketTitle("Updated Title".to_string())),
            description: None,
            status: None,
        };

        let response = warp::test::request()
            .method("PATCH")
            .path("/tickets/0")
            .json(&ticket_patch)
            .reply(&update_filter)
            .await;

        assert_eq!(response.status(), warp::http::StatusCode::NO_CONTENT);
    }

    #[tokio::test]
    async fn test_not_found() {
        let store = Arc::new(RwLock::new(TicketStore::new()));
        let get_filter = filters::tickets_filter(store.clone());

        let response = warp::test::request()
            .method("GET")
            .path("/tickets/999") // Assuming this ticket does not exist
            .reply(&get_filter)
            .await;

        assert_eq!(response.status(), warp::http::StatusCode::NOT_FOUND);
    }
}
