from pydantic import BaseModel
import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DbVkinderUsers(Base):
    __tablename__ = "Vkinder_users"

    id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True, nullable=False)
    viewed = sq.Column(sq.Boolean, nullable=False)
    favorites = sq.Column(sq.Boolean, nullable=False)
    banned = sq.Column(sq.Boolean, nullable=False)
    rating = sq.Column(sq.Integer, default=0)

    def __str__(self):
        return f"{self.vk_id} user.\n" \
               f"Viewed: {self.viewed}\n" \
               f"Banned: {self.banned}\n" \
               f"Favotite: {self.favorites}\n" \
               f"Rating of user: {self.rating}"


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def add_user_db(session,
                vk_id: int,
                rating: int,
                viewed: bool = False,
                banned: bool = False,
                favorites: bool = False):
    if check_user_in_db(session, vk_id):
        user_data = DbVkinderUsers(vk_id=vk_id,
                                   viewed=viewed,
                                   banned=banned,
                                   favorites=favorites,
                                   rating=rating)
        session.add(user_data)
        session.commit()


def check_user_in_db(session,
                     vk_id: int):
    return not bool(session.query(DbVkinderUsers).filter(DbVkinderUsers.id is vk_id).all())


def update_user_db(session,
                   vk_id: int,
                   rating: int,
                   viewed: bool = True,
                   banned: bool = False,
                   favorites: bool = False):
    session.query(DbVkinderUsers).filter(DbVkinderUsers.vk_id == vk_id).update({"viewed": viewed})
    session.query(DbVkinderUsers).filter(DbVkinderUsers.vk_id == vk_id).update({"banned": banned})
    session.query(DbVkinderUsers).filter(DbVkinderUsers.vk_id == vk_id).update({"favorites": favorites})
    session.query(DbVkinderUsers).filter(DbVkinderUsers.vk_id == vk_id).update({"rating": rating})

    session.commit()


def delete_user_db(session,
                   vk_id: int):
    session.query(DbVkinderUsers).filter(DbVkinderUsers.vk_id == vk_id).delete()
    session.commit()

class DisplayTypes(BaseModel):
    page: str = "page"
    popup: str = "popup"
    mobile: str = "mobile"


class ScopeTypes(BaseModel):
    FRIENDS: str = "friends"
    WALL: str = "wall"
    STATUS: str = "status"
    PHOTOS: str = "photos"
    GROUPS: str = "groups"
    STATS: str = "stats"
    OFFLINE: str = "offline"

    def _scope_dict(self):
        return self.dict()

    @property
    def scope(self):
        scope_list = []
        for pair in self._scope_dict().items():
            scope_list.append(pair[1])
        return ".".join(scope_list)
