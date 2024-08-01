create table created_chats(
    id integer primary key,
    contract_type text,
    chat_name text,
    users_in_chat text,
    link text
);

create table acces_users(
    id integer primary key,
    user_id int,
    product text,
    email text,
    sto_name text,
    permission int
);