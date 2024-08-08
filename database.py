import aiosqlite
from pydantic import BaseModel


class ContractChat(BaseModel):
    id: int
    contract_type: str
    chat_name: str
    users_in_chat: str
    link: str


class DataBase:
    def __init__(self, database_name: str) -> None:
        self.name = database_name
        self.conn = None


    async def create_connection(self) -> None:
        self.conn = await aiosqlite.connect(f"{self.name}.db")


    async def insert(self, table: str, values: dict) -> None:
        len_keys = len(values.keys())
        columns = ', '.join(values.keys())
        values = [tuple(values.values())]
        placeholders = ", ".join("?" * len_keys)

        await self.conn.executemany(
            f"INSERT INTO {table} "
            f"({columns}) "
            f"VALUES ({placeholders})",
            values)
        await self.conn.commit()


    async def get_chat_link(self, contract_type: str, user_name: str) -> tuple | None:
        all_data = await self.conn.execute("SELECT * FROM created_chats")
        rows = await all_data.fetchall()

        for row in rows:
            if (row[1] == contract_type) and (user_name in row[3].split(",")):
                return row
        
        return None


    async def get_acces_user_channel(self, user_id: int, product: str) -> tuple | None:
        all_data = await self.conn.execute("SELECT * FROM acces_users " +\
                                           "WHERE user_id=? AND product=?", 
                                           (user_id, product))
        rows = await all_data.fetchall()

        for row in rows:
            if row[1] == user_id and row[2] == product:
                return row

        return None


    async def update_acces_user_perm(self, user_id: int, product: str, permission: int) -> None:
        await self.conn.execute("UPDATE acces_users SET permission=?" +\
                                "WHERE user_id=? AND product=?", 
                                (permission, user_id, product))
        await self.conn.commit()


    async def get_all_user_ids(self) -> list:
        all_data = await self.conn.execute("SELECT user_id FROM users")
        rows = await all_data.fetchall()

        return [r[0] for r in rows]

    async def delete(self, table: str, id: int) -> None:
        await self.conn.execute(f"DELETE FROM {table} WHERE id={id};")
        await self.conn.commit()


    async def close(self) -> None:
        await self.conn.close()
