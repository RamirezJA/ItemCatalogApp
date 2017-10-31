from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import NC, Base, GameList, User

engine = create_engine('sqlite:///nintendolistwithusers.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Create dummy user
User1 = User(name="Super Mario", email="nintendo@protonmail.com",
             picture='http://s3.amazonaws.com/cdn.roosterteeth.com/uploads/'
                     'images/45c87974-bc64-49a3-9502-529d563fda8a/'
                     'md/jizzee44f75c08c3665.jpg')
session.add(User1)
session.commit()

# Nes Game list
nintendo1 = NC(user_id=1, name="Nes")

session.add(nintendo1)
session.commit()


game1 = GameList(user_id=1, name="Super Mario Bros. 3",
                 maker="Nintendo",
                 description=" The greatest mario game of its generation.",
                 price="$4.99", nintendo=nintendo1)

session.add(game1)
session.commit()

# Gameboy Game list
nintendo2 = NC(user_id=1, name="Gameboy")

session.add(nintendo2)
session.commit()

game1 = GameList(user_id=1, name="Pokemon Blue/Red",
                 maker="Nintendo",
                 description=" The game classic that started it all.",
                 price="$4.99", nintendo=nintendo2)

session.add(game1)
session.commit()

# SuperNes Game list
nintendo3 = NC(user_id=1, name="Super Nintendo")

session.add(nintendo3)
session.commit()

game1 = GameList(user_id=1, name="The Legend of Zelda: A Link to the Past",
                 maker="Nintendo", description=" A masterpiece",
                 price="$4.99", nintendo=nintendo3)

session.add(game1)
session.commit()

print "added games!"
