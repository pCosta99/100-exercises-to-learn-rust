#[cfg(test)]
mod tests {
    use intro_00::data::TicketDraft;
    use intro_00::store::{TicketId, TicketStore};
    use std::sync::Arc;
    use tokio::sync::{Mutex, RwLock};
    use tokio::time::{sleep, Duration};

    #[tokio::test]
    async fn test_concurrent_writes() {
        // Create a shared store wrapped in an Arc<RwLock>
        let store = Arc::new(RwLock::new(TicketStore::new()));

        // Spawn multiple tasks that attempt to write to the store
        let mut handles = vec![];
        for i in 0..5 {
            let store_clone = Arc::clone(&store);
            let handle = tokio::spawn(async move {
                let draft = TicketDraft::new(format!("Ticket {}", i), None);
                // Attempt to add a ticket
                store_clone.write().await.add_ticket(draft);
                sleep(Duration::from_millis(100)).await; // Simulate some work
            });
            handles.push(handle);
        }

        // Wait for all tasks to complete
        for handle in handles {
            let _ = handle.await;
        }

        // After all writes, ensure that the store has the expected number of tickets
        let store_guard = store.read().await;
        assert_eq!(store_guard.tickets.len(), 5);
    }

    #[tokio::test]
    async fn test_concurrent_reads_count() {
        let store = Arc::new(RwLock::new(TicketStore::new()));
        let counter = Arc::new(Mutex::new(0)); // Counter for successful reads
        let mut handles = vec![];

        // Prepopulate the store with tickets
        store
            .write()
            .await
            .add_ticket(TicketDraft::new("First Ticket".to_string(), None));
        store
            .write()
            .await
            .add_ticket(TicketDraft::new("Second Ticket".to_string(), None));

        let num_reads = 3;

        for _ in 0..num_reads {
            let store_clone = Arc::clone(&store);
            let counter_clone = Arc::clone(&counter);

            let handle = tokio::spawn(async move {
                let ticket_id = TicketId(0);

                {
                    let store_guard = store_clone.read().await;
                    let ticket_lock = store_guard.get(ticket_id).unwrap();
                    let ticket_guard = ticket_lock.read().ok().unwrap();
                    let _ = ticket_guard.clone();
                };

                let mut count = counter_clone.lock().await;
                *count += 1
            });

            handles.push(handle);
        }

        for handle in handles {
            handle.await.unwrap();
        }

        let final_count = counter.lock().await;
        assert_eq!(
            *final_count, num_reads,
            "Expected {} successful reads, but got {}",
            num_reads, *final_count
        );
    }
}

