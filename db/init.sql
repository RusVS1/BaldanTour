CREATE TABLE tours IF NOT EXISTS (
    id SERIAL NOT NULL,
    last_update TIMESTAMP,
    photo_link TEXT,
    point_begin VARCHAR() NOT NULL,
    point_end VARCHAR() NOT NULL,
    flight_date DATE NOT NULL,
    night_number INTEGER NOT NULL,
    people_number INTEGER NOT NULL,
    hot BOOLEAN NOT NULL, 
    recreation_type VARCHAR(),
    price NUMERIC NOT NULL,
    hotel_name VARCHAR() NOT NULL,
    hotel_category INTEGER,
    hotel_rating NUMERIC,
    hotel_type VARCHAR(),
    food_type VARCHAR(),
    description TEXT,
    link TEXT NOT NULL
);

CREATE users IF NOT EXISTS (
    id SERIAL NOT NULL,
    login VARCHAR() NOT NULL,
    password_hash VARCHAR() NOT NULL
);

CREATE favorite_tours IF NOT EXISTS (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    tour_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (tour_id) REFERENCES tours(id) ON DELETE CASCADE
);