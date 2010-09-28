from helpers import *
from radarpost.user import User

def test_user_password():

    user = User(username='joe', password='fr3d')
    
    
    assert user.username == 'joe'
    assert user.check_password('fr3d')
    assert not user.check_password('fr01d')
    
    db = create_test_users_db()
    
    user.store(db)
    user = User.load(db, user.id)
    
    assert user.check_password('fr3d')
    assert not user.check_password('fr01d')
    assert user.username == 'joe'


def test_user_id_requirement():
    user = User(username='joe', password='fr3d')
    
    assert user.username == 'joe'
    assert user.id == "org.couchdb.user:joe"

    db = create_test_users_db()
    
    user.store(db)
    user = User.load(db, "org.couchdb.user:joe")
    assert user.username == 'joe'
    
    user = User.get_by_username(db, "joe")
    assert user.username == 'joe'
    assert user.id == "org.couchdb.user:joe"
