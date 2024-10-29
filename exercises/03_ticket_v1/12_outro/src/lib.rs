// TODO: Define a new `Order` type.
//   It should keep track of three pieces of information: `product_name`, `quantity`, and `unit_price`.
//   The product name can't be empty and it can't be longer than 300 bytes.
//   The quantity must be strictly greater than zero.
//   The unit price is in cents and must be strictly greater than zero.
//   Order must include a method named `total` that returns the total price of the order.
//   Order must provide setters and getters for each field.
//
// Tests are located in a different place this time—in the `tests` folder.
// The `tests` folder is a special location for `cargo`. It's where it looks for **integration tests**.
// Integration here has a very specific meaning: they test **the public API** of your project.
// You'll need to pay attention to the visibility of your types and methods; integration
// tests can't access private or `pub(crate)` items.

pub struct Order {
    product_name: String,
    quantity: u32,
    unit_price: u32
}

impl Order {
    fn valid_product_name(product_name: String) {
        if product_name.is_empty() {
            panic!("Product name can't be empty!")
        }

        if product_name.len() > 300 {
            panic!("Product name can't be bigger than 300 letters!")
        }
    }

    fn valid_quantity(quantity: u32) {
        if quantity <= 0 {
            panic!("Quantity must be bigger than zero!")
        }
    }

    fn valid_unit_price(unit_price: u32) {
        if unit_price <= 0 {
            panic!("Unit price must be bigger than zero!")
        }
    }

    pub fn new(product_name: String, quantity: u32, unit_price: u32) -> Self {
        Self::valid_product_name(product_name.clone());
        Self::valid_quantity(quantity);
        Self::valid_unit_price(unit_price);

        Self { product_name, quantity, unit_price }
    }

    pub fn product_name(&self) -> &String {
        &self.product_name
    }

    pub fn quantity(&self) -> &u32 {
        &self.quantity
    }

    pub fn unit_price(&self) -> &u32 {
        &self.unit_price
    }

    pub fn set_product_name(&mut self, product_name: String) {
        Self::valid_product_name(product_name.clone());

        self.product_name = product_name;
    }

    pub fn set_quantity(&mut self, quantity: u32) {
        Self::valid_quantity(quantity);

        self.quantity = quantity;
    }

    pub fn set_unit_price(&mut self, unit_price: u32) {
        Self::valid_unit_price(unit_price);

        self.unit_price = unit_price;
    }

    pub fn total(&self) -> u32 {
        &self.quantity * &self.unit_price
    }
}
