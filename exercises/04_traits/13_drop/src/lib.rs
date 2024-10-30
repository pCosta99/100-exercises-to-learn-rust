// TODO: implement a so-called "Drop bomb": a type that panics when dropped
//  unless a certain operation has been performed on it.
//  You can see the expected API in the tests below.

#[derive(Clone)]
struct DropBomb<'a> {
    name: &'a str,
}

impl DropBomb<'_> {
    fn new() -> Self {
        DropBomb {
            name: "hi",
        }
    }

    fn defuse(&mut self) {
        self.name = ""
    }
}

impl Drop for DropBomb<'_> {
    fn drop(&mut self) {
        if self.name != "" {
            panic!("nooooooooooooooo!")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[should_panic]
    fn test_drop_bomb() {
        let bomb = DropBomb::new();
        // The bomb should panic when dropped
    }

    #[test]
    fn test_defused_drop_bomb() {
        let mut bomb = DropBomb::new();
        bomb.defuse();
        // The bomb should not panic when dropped
        // since it has been defused
    }
}
