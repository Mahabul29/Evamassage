from pymongo.errors import DuplicateKeyError  # add this import at the top

def create_user(username, password, full_name):
    if len(username) < 3 or len(password) < 4:
        return None, "Invalid input"

    username = username.lower()  # normalize BEFORE the duplicate check

    if users.find_one({'username': username}):
        return None, "Username exists"

    user_id = secrets.randbelow(1000000000)
    user = {
        'user_id': user_id,
        'username': username,  # already lowercased, no need for username.lower()
        'password': hash_password(password),
        'full_name': full_name or username,
        'bio': '',
        'avatar': 'default',
        'language': 'en',
        'theme': 'light',
        'text_size': 'medium',
        'auto_delete': 'never',
        'created_at': datetime.now()
    }
    try:
        users.insert_one(user)
    except DuplicateKeyError:
        return None, "Username exists"

    return user, "Success"
