"""
Generate the sample SQLite database.

Creates company.db from schema.sql and fills it with realistic fake data.
Uses a fixed random seed, so every run produces exactly the same data.

Run from the backend folder:
    python app/db/seed.py
"""

import random
import sqlite3
from datetime import date
from pathlib import Path

from faker import Faker

DB_DIR = Path(__file__).parent
SCHEMA_PATH = DB_DIR / "schema.sql"
DB_PATH = DB_DIR / "company.db"

SEED = 42

fake = Faker("en_US")
fake_uk = Faker("en_GB")
fake_ca = Faker("en_CA")
Faker.seed(SEED)
random.seed(SEED)

DEPARTMENTS = [
    ("Executive", "New York"),
    ("Sales", "New York"),
    ("Engineering", "San Francisco"),
    ("Marketing", "Chicago"),
    ("Finance", "New York"),
    ("Human Resources", "Chicago"),
    ("Customer Support", "Austin"),
    ("Operations", "Austin"),
]

CATEGORIES = ["Electronics", "Books", "Clothing", "Home & Kitchen", "Sports", "Toys"]

# department: (staff job title, headcount, min salary, max salary)
STAFF_ROLES = {
    "Sales": ("Sales Representative", 15, 45_000, 80_000),
    "Engineering": ("Software Engineer", 9, 85_000, 110_000),
    "Marketing": ("Marketing Specialist", 5, 50_000, 85_000),
    "Finance": ("Financial Analyst", 4, 60_000, 95_000),
    "Human Resources": ("HR Specialist", 3, 50_000, 75_000),
    "Customer Support": ("Support Agent", 4, 45_000, 60_000),
    "Operations": ("Operations Coordinator", 2, 50_000, 70_000),
}

CUSTOMER_COUNT = 200
US_CUSTOMER_SHARE = 0.8

# Real (city, state code) pairs, so city and state always match.
US_CITIES = [
    ("Los Angeles", "CA"),
    ("San Francisco", "CA"),
    ("San Diego", "CA"),
    ("San Jose", "CA"),
    ("New York", "NY"),
    ("Buffalo", "NY"),
    ("Austin", "TX"),
    ("Houston", "TX"),
    ("Dallas", "TX"),
    ("Miami", "FL"),
    ("Orlando", "FL"),
    ("Chicago", "IL"),
    ("Seattle", "WA"),
    ("Boston", "MA"),
    ("Denver", "CO"),
    ("Phoenix", "AZ"),
    ("Atlanta", "GA"),
    ("Portland", "OR"),
]
UK_CITIES = ["London", "Manchester", "Birmingham", "Edinburgh", "Bristol"]
CANADA_CITIES = ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa"]

# category: (min price, max price, product names)
PRODUCTS = {
    "Electronics": (50, 1500, [
        "Wireless Headphones", "Smartwatch", "4K Monitor", "Bluetooth Speaker", "Laptop",
        "Tablet", "Mechanical Keyboard", "Wireless Mouse", "Webcam", "External SSD",
    ]),
    "Books": (10, 60, [
        "Python Programming Guide", "SQL for Beginners", "The Data Science Handbook",
        "Mystery at Midnight", "The Lost Kingdom", "Cooking Made Simple", "History of Rome",
        "Personal Finance 101", "Space Exploration", "Mindful Living",
    ]),
    "Clothing": (15, 150, [
        "Denim Jacket", "Running Shoes", "Cotton T-Shirt", "Wool Sweater", "Rain Coat",
        "Leather Belt", "Baseball Cap", "Hiking Boots", "Yoga Pants", "Winter Gloves",
    ]),
    "Home & Kitchen": (20, 400, [
        "Coffee Maker", "Blender", "Air Fryer", "Chef Knife Set", "Non-Stick Pan",
        "Vacuum Cleaner", "Desk Lamp", "Bath Towel Set", "Stand Mixer", "Water Filter",
    ]),
    "Sports": (15, 300, [
        "Yoga Mat", "Dumbbell Set", "Tennis Racket", "Basketball", "Cycling Helmet",
        "Jump Rope", "Camping Tent", "Soccer Ball", "Resistance Bands", "Water Bottle",
    ]),
    "Toys": (10, 100, [
        "Building Blocks Set", "Remote Control Car", "Jigsaw Puzzle", "Board Game", "Plush Bear",
        "Toy Train Set", "Art Supplies Kit", "Dollhouse", "Science Experiment Kit", "Kite",
    ]),
}

ORDER_COUNT = 1000
ORDERS_START = date(2023, 1, 1)
ORDERS_END = date(2025, 12, 31)
RECENT_ORDERS_FROM = date(2025, 12, 1)   # orders after this are still pending or shipped
NO_ORDERS_SIGNUP_FROM = date(2025, 10, 1)  # customers who signed up after this have no orders yet
NEVER_ORDERED_PRODUCTS = 2                 # the last N products are never ordered

used_emails: set[str] = set()


def create_database() -> sqlite3.Connection:
    """Delete any old database file and create a fresh, empty one from schema.sql."""
    DB_PATH.unlink(missing_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def seed_departments(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO departments (name, location) VALUES (?, ?)",
        DEPARTMENTS,
    )


def seed_categories(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO categories (name) VALUES (?)",
        [(name,) for name in CATEGORIES],
    )


def unique_email(first: str, last: str, domain: str) -> str:
    """Build 'first.last@domain', adding a number if that address is already taken."""
    base = f"{first}.{last}".lower().replace("'", "")
    email = f"{base}@{domain}"
    n = 2
    while email in used_emails:
        email = f"{base}{n}@{domain}"
        n += 1
    used_emails.add(email)
    return email


def random_date(start: date, end: date) -> str:
    """Random date between start and end, as 'YYYY-MM-DD' text."""
    return fake.date_between(start_date=start, end_date=end).isoformat()


def insert_employee(
    conn: sqlite3.Connection,
    job_title: str,
    salary: int,
    hire_date: str,
    department_id: int,
    manager_id: int | None,
) -> int:
    """Insert one employee with a random name and return their new employee_id."""
    first, last = fake.first_name(), fake.last_name()
    cursor = conn.execute(
        """
        INSERT INTO employees
            (first_name, last_name, email, job_title, salary, hire_date, department_id, manager_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            first,
            last,
            unique_email(first, last, "company.com"),
            job_title,
            salary,
            hire_date,
            department_id,
            manager_id,
        ),
    )
    return cursor.lastrowid


def seed_employees(conn: sqlite3.Connection) -> None:
    """CEO at the top, one head per department reporting to the CEO, staff reporting to their head."""
    department_ids = dict(conn.execute("SELECT name, department_id FROM departments"))

    ceo_id = insert_employee(
        conn,
        job_title="Chief Executive Officer",
        salary=250_000,
        hire_date="2018-01-15",
        department_id=department_ids["Executive"],
        manager_id=None,
    )

    for department, (job_title, headcount, min_salary, max_salary) in STAFF_ROLES.items():
        head_id = insert_employee(
            conn,
            job_title=f"Head of {department}",
            salary=random.randrange(120_000, 180_001, 1_000),
            hire_date=random_date(date(2018, 1, 1), date(2020, 12, 31)),
            department_id=department_ids[department],
            manager_id=ceo_id,
        )
        for _ in range(headcount):
            insert_employee(
                conn,
                job_title=job_title,
                salary=random.randrange(min_salary, max_salary + 1, 1_000),
                hire_date=random_date(date(2019, 1, 1), date(2025, 12, 31)),
                department_id=department_ids[department],
                manager_id=head_id,
            )


def seed_customers(conn: sqlite3.Connection) -> None:
    """About 80% US customers (with a state code), the rest from the UK or Canada (state NULL)."""
    rows = []
    for _ in range(CUSTOMER_COUNT):
        if random.random() < US_CUSTOMER_SHARE:
            name_faker, country = fake, "USA"
            city, state = random.choice(US_CITIES)
        elif random.random() < 0.5:
            name_faker, country = fake_uk, "UK"
            city, state = random.choice(UK_CITIES), None
        else:
            name_faker, country = fake_ca, "Canada"
            city, state = random.choice(CANADA_CITIES), None

        first, last = name_faker.first_name(), name_faker.last_name()
        rows.append(
            (
                first,
                last,
                unique_email(first, last, fake.free_email_domain()),
                city,
                state,
                country,
                random_date(date(2022, 1, 1), date(2025, 12, 31)),
            )
        )

    conn.executemany(
        """
        INSERT INTO customers
            (first_name, last_name, email, city, state, country, signup_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def random_stock() -> int:
    """Mostly healthy stock, but some low (under 10) and a few out of stock (0)."""
    roll = random.random()
    if roll < 0.05:
        return 0
    if roll < 0.15:
        return random.randint(1, 9)
    return random.randint(20, 500)


def seed_products(conn: sqlite3.Connection) -> None:
    category_ids = dict(conn.execute("SELECT name, category_id FROM categories"))
    rows = []
    for category, (min_price, max_price, names) in PRODUCTS.items():
        for name in names:
            price = round(random.uniform(min_price, max_price)) - 0.01  # e.g. 49.99
            rows.append((name, category_ids[category], price, random_stock()))

    conn.executemany(
        "INSERT INTO products (name, category_id, price, stock_quantity) VALUES (?, ?, ?, ?)",
        rows,
    )


def order_status(order_date: str) -> str:
    """Recent orders are still in progress; older ones were delivered or cancelled."""
    if order_date >= RECENT_ORDERS_FROM.isoformat():
        return random.choice(["pending", "shipped"])
    return "cancelled" if random.random() < 0.12 else "delivered"


def seed_orders(conn: sqlite3.Connection) -> None:
    """Insert orders, each with 1-5 different products in order_items."""
    customers = conn.execute(
        "SELECT customer_id, signup_date FROM customers WHERE signup_date < ?",
        (NO_ORDERS_SIGNUP_FROM.isoformat(),),
    ).fetchall()
    sales_rep_ids = [
        row[0]
        for row in conn.execute(
            "SELECT employee_id FROM employees WHERE job_title = 'Sales Representative'"
        )
    ]
    products = conn.execute("SELECT product_id, price FROM products").fetchall()
    orderable_products = products[:-NEVER_ORDERED_PRODUCTS]

    for _ in range(ORDER_COUNT):
        customer_id, signup_date = random.choice(customers)
        first_possible_date = max(date.fromisoformat(signup_date), ORDERS_START)
        order_date = random_date(first_possible_date, ORDERS_END)

        cursor = conn.execute(
            "INSERT INTO orders (customer_id, employee_id, order_date, status) VALUES (?, ?, ?, ?)",
            (customer_id, random.choice(sales_rep_ids), order_date, order_status(order_date)),
        )
        order_id = cursor.lastrowid

        items = []
        for product_id, price in random.sample(orderable_products, k=random.randint(1, 5)):
            quantity = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
            discount = random.choice([0.05, 0.10, 0.15]) if random.random() < 0.3 else 0
            unit_price = round(price * (1 - discount), 2)
            items.append((order_id, product_id, quantity, unit_price))

        conn.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            items,
        )


if __name__ == "__main__":
    conn = create_database()
    seed_departments(conn)
    seed_categories(conn)
    seed_employees(conn)
    seed_customers(conn)
    seed_products(conn)
    seed_orders(conn)
    conn.commit()
    conn.close()
    print(f"Created database at {DB_PATH}")
