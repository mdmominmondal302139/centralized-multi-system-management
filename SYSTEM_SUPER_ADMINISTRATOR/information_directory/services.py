from datetime import datetime, timezone
from bson import ObjectId
from DATABASE.mongodb import get_database, clean

ROLE = 'SYSTEM_SUPER_ADMINISTRATOR'
COLLECTION = 'information_directory'
CATEGORIES = ('Doctors', 'Hospital', 'Teacher', 'School', 'College', 'Training Center', 'Bank & Finance')

def _guard(context):
    if not isinstance(context, dict) or context.get('role') != ROLE:
        raise PermissionError('Access denied.')

def list_records(context, filters=None):
    _guard(context)
    filters = filters or {}
    db = get_database()
    query = {}
    search = str(filters.get('search') or '').strip()
    category = str(filters.get('category') or '').strip()
    if search:
        query['$or'] = [{k: {'$regex': search, '$options': 'i'}} for k in ('name','category','mobile','phone','contact','email','institution','hospital_clinic','branch_name','address','district','upazila','area','specialization','subject','eiin')]
    if category and category in CATEGORIES:
        query['category'] = category
    return [clean(x) for x in db[COLLECTION].find(query).sort('_id', -1).limit(500)]

def create_record(context, data):
    _guard(context)
    item = dict(data or {})
    item.pop('action', None)
    item.update({'created_at': datetime.now(timezone.utc), 'updated_at': datetime.now(timezone.utc), 'created_by': context.get('user_id'), 'created_by_role': ROLE})
    result = get_database()[COLLECTION].insert_one(item)
    return str(result.inserted_id)

def update_record(context, record_id, data):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id
    item = dict(data or {})
    item.pop('_id', None)
    item.pop('action', None)
    item['updated_at'] = datetime.now(timezone.utc)
    result = get_database()[COLLECTION].update_one({'_id': oid}, {'$set': item})
    return result.modified_count or result.matched_count

def delete_record(context, record_id):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id
    result = get_database()[COLLECTION].delete_one({'_id': oid})
    return result.deleted_count
