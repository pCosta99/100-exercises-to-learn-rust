use anyhow::anyhow;
use serde::Serialize;
use tokio::io::AsyncReadExt;
use tokio::net::TcpStream;

pub async fn parse_body<'a>(
    socket: &mut TcpStream,
    request: &mut httparse::Request<'a, 'a>,
    buffer: &'a [u8],
    parse_result: Option<httparse::Status<usize>>,
) -> Result<String, anyhow::Error> {
    let content_length = request
        .headers
        .iter()
        .find(|header| header.name.eq_ignore_ascii_case("content-length"))
        .and_then(|header| {
            std::str::from_utf8(header.value)
                .ok()?
                .parse::<usize>()
                .ok()
        })
        .unwrap_or(0);

    if let Some(httparse::Status::Complete(idx)) = parse_result {
        let body = &buffer[idx..];

        let body = if body.len() < content_length {
            let mut remaining_body = vec![0; content_length - body.len()];
            socket.read_exact(&mut remaining_body).await.unwrap();
            let complete_body = [body, &remaining_body].concat();
            String::from_utf8_lossy(&complete_body)
                .into_owned()
                .trim_matches(char::from(0))
                .to_string()
        } else {
            String::from_utf8_lossy(&body)
                .into_owned()
                .trim_matches(char::from(0))
                .to_string()
        };

        Ok(body)
    } else {
        Err(anyhow!("Failed to parse body"))
    }
}

pub enum Response<T>
where
    T: Serialize,
{
    Ok(T),
    Created(T),
    NoContent,
}

impl Response<()> {
    pub const NO_CONTENT: Self = Response::NoContent;
}

pub async fn build_response<T>(response: Response<T>) -> Vec<u8>
where
    T: Serialize,
{
    match response {
        Response::Ok(x) => {
            let body = serde_json::to_string(&x).unwrap_or_else(|_| "{}".to_string());
            format!(
                "HTTP/1.1 200 OK\r\nContent-Length: {}\r\n\r\n{}",
                body.len(),
                body
            )
        }
        Response::Created(x) => {
            let body = serde_json::to_string(&x).unwrap_or_else(|_| "{}".to_string());
            format!(
                "HTTP/1.1 201 Created\r\nContent-Length: {}\r\n\r\n{}",
                body.len(),
                body
            )
        }
        Response::NoContent => format!("HTTP/1.1 204 No Content\r\n"),
    }
    .into_bytes()
}
