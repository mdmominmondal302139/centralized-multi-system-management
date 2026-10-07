from datetime import datetime, timezone
from bson import ObjectId
from DATABASE.mongodb import get_database, clean

ROLE = 'SYSTEM_SUPER_ADMINISTRATOR'
COLLECTION = 'branches'
LEGACY_COLLECTION = 'branch_management'


def _guard(context):
    if not isinstance(context, dict) or context.get('role') != ROLE:
        raise PermissionError('Access denied.')


def _query(filters):
    filters = filters or {}
    query = {}
    for key in ('search', 'date', 'month', 'member', 'branch', 'status'):
        value = str(filters.get(key) or '').strip()
        if not value:
            continue
        if key == 'search':
            query['$or'] = [
                {k: {'$regex': value, '$options': 'i'}}
                for k in ('name', 'username', 'email', 'phone', 'note', 'source', 'member_name', 'branch_name', 'branch_reg_no', 'type', 'status', 'division', 'district', 'location')
            ]
        elif key == 'month':
            query['date'] = {'$regex': f'^{value}'}
        elif key == 'member':
            query['$or'] = [
                {'member_name': {'$regex': value, '$options': 'i'}},
                {'member_id': {'$regex': value, '$options': 'i'}},
            ]
        elif key == 'branch':
            query['branch_name'] = {'$regex': value, '$options': 'i'}
        else:
            query[key] = value
    return query


def list_records(context, filters=None):
    _guard(context)
    db = get_database()
    query = _query(filters)
    primary = [clean(x) for x in db[COLLECTION].find(query).sort('_id', -1).limit(500)]
    legacy = [clean(x) for x in db[LEGACY_COLLECTION].find(query).sort('_id', -1).limit(500)]

    records = []
    seen = set()
    for row, source in [(x, COLLECTION) for x in primary] + [(x, LEGACY_COLLECTION) for x in legacy]:
        key = (
            str(row.get('branch_reg_no') or '').strip().lower(),
            str(row.get('branch_name') or row.get('name') or '').strip().lower(),
            str(row.get('district') or '').strip().lower(),
        )
        if key == ('', '', ''):
            key = ('_id', str(row.get('_id')))
        if key in seen:
            continue
        seen.add(key)
        row['_source_collection'] = source
        records.append(row)
    return records[:500]


def create_record(context, data):
    _guard(context)
    item = dict(data or {})
    item.pop('action', None)
    now = datetime.now(timezone.utc)
    item.update({'created_at': now, 'updated_at': now, 'created_by': context.get('user_id'), 'created_by_role': ROLE})
    result = get_database()[COLLECTION].insert_one(item)
    return str(result.inserted_id)


def _collection(source):
    return LEGACY_COLLECTION if source == LEGACY_COLLECTION else COLLECTION


def update_record(context, record_id, data, source=None):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id
    item = dict(data or {})
    item.pop('_id', None)
    item.pop('action', None)
    item.pop('record_id', None)
    item.pop('_source_collection', None)
    item['updated_at'] = datetime.now(timezone.utc)
    return get_database()[_collection(source)].update_one({'_id': oid}, {'$set': item}).modified_count


def delete_record(context, record_id, source=None):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id
    return get_database()[_collection(source)].delete_one({'_id': oid}).deleted_count
