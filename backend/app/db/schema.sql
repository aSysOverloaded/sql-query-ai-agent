-- Sample database schema for the SQL Query AI Agent.
-- A small retail company: departments, employees, customers, products and orders.

CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE,
    location      TEXT    NOT NULL
);

CREATE TABLE employees (
    employee_id   INTEGER        PRIMARY KEY,
    first_name    TEXT           NOT NULL,
    last_name     TEXT           NOT NULL,
    email         TEXT           NOT NULL UNIQUE,
    job_title     TEXT           NOT NULL,
    salary        DECIMAL(10, 2) NOT NULL,
    hire_date     TEXT           NOT NULL,  -- 'YYYY-MM-DD'
    department_id INTEGER        NOT NULL REFERENCES departments (department_id),
    manager_id    INTEGER        REFERENCES employees (employee_id)  -- NULL for the top-level manager
);

CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    first_name    TEXT    NOT NULL,
    last_name     TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    city          TEXT    NOT NULL,
    state         TEXT,             -- 2-letter code like 'CA'; NULL outside the USA
    country       TEXT    NOT NULL, -- e.g. 'USA', 'Canada', 'UK'
    signup_date   TEXT    NOT NULL  -- 'YYYY-MM-DD'
);

CREATE TABLE categories (
    category_id   INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE
);

CREATE TABLE products (
    product_id     INTEGER        PRIMARY KEY,
    name           TEXT           NOT NULL,
    category_id    INTEGER        NOT NULL REFERENCES categories (category_id),
    price          DECIMAL(10, 2) NOT NULL,  -- current list price
    stock_quantity INTEGER        NOT NULL   -- units currently in stock
);

CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers (customer_id),
    employee_id   INTEGER NOT NULL REFERENCES employees (employee_id),  -- sales rep who handled the order
    order_date    TEXT    NOT NULL,  -- 'YYYY-MM-DD'
    status        TEXT    NOT NULL
                  CHECK (status IN ('pending', 'shipped', 'delivered', 'cancelled'))
);

CREATE TABLE order_items (
    order_item_id INTEGER        PRIMARY KEY,
    order_id      INTEGER        NOT NULL REFERENCES orders (order_id),
    product_id    INTEGER        NOT NULL REFERENCES products (product_id),
    quantity      INTEGER        NOT NULL,
    unit_price    DECIMAL(10, 2) NOT NULL  -- price at time of purchase; revenue = quantity * unit_price
);
