CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(200) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE tag (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE post (
    post_id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    media_type VARCHAR(20) CHECK (media_type IN ('video', 'photo', 'none')),
    thumb_url TEXT,
    description TEXT
);

CREATE TABLE post_tag (
    post_id INTEGER NOT NULL REFERENCES post(post_id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tag(tag_id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);

CREATE TABLE time (
    time_id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES post(post_id) ON DELETE CASCADE,
    year INTEGER CHECK (year >= 0)
);

CREATE TABLE post_like (
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES post(post_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, post_id) 
);

CREATE TABLE comments (
    comment_id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES post(post_id) ON DELETE CASCADE,
    user_id INTEGER,
    parent_comment_id INTEGER REFERENCES comments(comment_id) ON DELETE CASCADE,
    text TEXT
);
