import json

from multiprocessing import Lock
from enum import Enum
from datetime import datetime
from db import get_db, get_db_version
from pymysql.cursors import DictCursor
from util.flaskjson import CustomJSONEncoder

calc_stat_lock = Lock()
class AggregateStat(Enum):
    USERS = 'total_users',
    GOOGLE_USERS = 'total_google_users',

    RUNS = 'total_runs',
    FINISHED_RUNS = 'total_finished_runs',
    USER_RUNS = 'total_user_runs',
    FINISHED_USER_RUNS = 'total_finished_user_runs',

    QUICK_RUNS = 'total_quick_runs',
    FINISHED_QUICK_RUNS = 'total_finished_quick_runs',
    USER_QUICK_RUNS = 'total_user_quick_runs',
    FINISHED_USER_QUICK_RUNS = 'total_finished_user_quick_runs',

    MARATHONS = 'total_marathons',
    FINISHED_MARATHONS = 'total_finished_marathons',
    USER_MARATHONS = 'total_user_marathons',
    FINISHED_USER_MARATHONS = 'total_finished_user_marathons',

    LOBBIES = 'total_created_lobbies',
    LOBBY_RUNS = 'total_lobby_runs',
    FINISHED_LOBBY_RUNS = 'total_finished_lobby_runs'

AggStat = AggregateStat

def calculate() -> dict:
    totals_json = _calculate_total_stats()
    daily_json = _calculate_daily_stats()

    merged_json = totals_json
    merged_json.update(daily_json)

    stat_json_str = json.dumps({
        'version': get_db_version(),
        'stats': merged_json
    }, cls=CustomJSONEncoder)

    query = '''
    INSERT INTO `computed_stats` (`stats_json`, `timestamp`) 
    VALUES (%s, %s)
    '''

    db = get_db()
    with db.cursor(cursor=DictCursor) as cursor:
        cursor.execute(query, (stat_json_str, datetime.now())) 

    db.commit()

def _calculate_total_stats():
    queries = {}
    queries[AggStat.USERS] = "SELECT COUNT(*) AS users_total FROM users"
    queries[AggStat.GOOGLE_USERS] = 'SELECT COUNT(*) AS goog_total FROM users WHERE hash=""'

    queries[AggStat.RUNS] = "SELECT COUNT(*) AS sprints_total FROM sprint_runs"
    queries[AggStat.FINISHED_RUNS] = "SELECT COUNT(*) AS sprints_finished FROM sprint_runs WHERE finished"
    queries[AggStat.USER_RUNS] = "SELECT COUNT(*) AS user_runs FROM sprint_runs WHERE user_id IS NOT NULL"
    queries[AggStat.FINISHED_USER_RUNS] = "SELECT COUNT(*) AS user_finished_runs FROM sprint_runs WHERE user_id IS NOT NULL AND finished"

    queries[AggStat.QUICK_RUNS] = "SELECT COUNT(*) AS quick_runs_total FROM quick_runs"
    queries[AggStat.FINISHED_QUICK_RUNS] = "SELECT COUNT(*) AS quick_runs_finished FROM quick_runs WHERE finished"
    queries[AggStat.USER_QUICK_RUNS] = "SELECT COUNT(*) AS user_quick_runs FROM quick_runs WHERE user_id IS NOT NULL"
    queries[AggStat.FINISHED_USER_QUICK_RUNS] = "SELECT COUNT(*) AS user_finished_quick_runs FROM quick_runs WHERE user_id IS NOT NULL AND finished"

    queries[AggStat.MARATHONS] = "SELECT COUNT(*) AS marathons_total FROM marathonruns"
    queries[AggStat.FINISHED_MARATHONS] = "SELECT COUNT(*) AS marathons_finished FROM marathonruns where finished=TRUE"
    queries[AggStat.USER_MARATHONS] = "SELECT COUNT(*) AS user_marathons FROM marathonruns WHERE user_id IS NOT NULL"
    queries[AggStat.FINISHED_USER_MARATHONS] = "SELECT COUNT(*) AS user_finished_marathons FROM marathonruns WHERE user_id IS NOT NULL AND finished=TRUE"
    
    queries[AggStat.LOBBIES] = "SELECT COUNT(*) AS lobbies_created FROM lobbys"
    queries[AggStat.LOBBY_RUNS] = "SELECT COUNT(*) AS lobby_runs_total FROM lobby_runs"
    queries[AggStat.FINISHED_LOBBY_RUNS] = "SELECT COUNT(*) AS lobby_runs_finished FROM lobby_runs WHERE user_id IS NOT NULL AND finished=TRUE"
    results = {}

    db = get_db()
    with db.cursor(cursor=DictCursor) as cursor:
        for _, query in queries.items():
            cursor.execute(query)
            results.update(cursor.fetchall()[0])
    
    return results

def _calculate_daily_stats():
    queries = {}
    queries['daily_new_users'] = '''
    WITH data AS (
        SELECT 
            DATE(join_date) AS day,
            COUNT(*) AS daily_users 
        FROM users  
        GROUP BY day 
    )

    SELECT
        day,
        daily_users,
        SUM(daily_users) OVER (ORDER BY day) AS total 
    FROM data
    '''

    queries['daily_sprints'] = '''
    WITH data AS (
        SELECT 
            DATE(start_time) AS day,
            COUNT(*) AS daily_plays 
        FROM sprint_runs
        WHERE start_time IS NOT NULL
        GROUP BY day 
    )

    SELECT
        day,
        daily_plays,
        SUM(daily_plays) OVER (ORDER BY day) AS total 
    FROM data
    '''

    queries['daily_finished_sprints'] = '''
    WITH data AS (
        SELECT 
            DATE(start_time) AS day,
            COUNT(*) AS daily_plays 
        FROM sprint_runs
        WHERE finished
        GROUP BY day 
    )

    SELECT
        day,
        daily_plays,
        SUM(daily_plays) OVER (ORDER BY day) AS total 
    FROM data
    '''
    
    queries['daily_lobby_runs'] = '''
    WITH data AS (
        SELECT 
            DATE(start_time) AS day,
            COUNT(*) AS daily_plays 
        FROM lobby_runs
        WHERE start_time IS NOT NULL
        GROUP BY day 
    )

    SELECT
        day,
        daily_plays,
        SUM(daily_plays) OVER (ORDER BY day) AS total 
    FROM data
    '''
        
    queries['daily_finished_lobby_runs'] = '''
    WITH data AS (
        SELECT 
            DATE(start_time) AS day,
            COUNT(*) AS daily_plays 
        FROM lobby_runs
        WHERE finished
        GROUP BY day 
    )

    SELECT
        day,
        daily_plays,
        SUM(daily_plays) OVER (ORDER BY day) AS total 
    FROM data
    '''
    
    queries['daily_quick_runs'] = '''
    WITH data AS (
        SELECT 
            DATE(start_time) AS day,
            COUNT(*) AS daily_plays 
        FROM quick_runs
        WHERE start_time IS NOT NULL
        GROUP BY day 
    )

    SELECT
        day,
        daily_plays,
        SUM(daily_plays) OVER (ORDER BY day) AS total 
    FROM data
    '''

    queries['daily_finished_quick_runs'] = '''
    WITH data AS (
        SELECT 
            DATE(start_time) AS day,
            COUNT(*) AS daily_plays 
        FROM quick_runs
        WHERE finished
        GROUP BY day 
    )

    SELECT
        day,
        daily_plays,
        SUM(daily_plays) OVER (ORDER BY day) AS total 
    FROM data
    '''

    queries['daily_created_lobbies'] = '''
    WITH data AS (
        SELECT
            DATE(create_date) AS day,
            COUNT(*) as daily_created_lobbies
        FROM lobbys
        WHERE create_date IS NOT NULL
        GROUP BY day
    )
    
    SELECT
        day,
        daily_created_lobbies,
        SUM(daily_created_lobbies) OVER (ORDER BY day) AS total
    FROM data
    '''

    queries['avg_user_plays'] = '''
    WITH data AS (
        SELECT user_id,
        DATE(start_time) AS day,
        COUNT(*) AS plays
        FROM sprint_runs
        WHERE user_id IS NOT NULL 
            AND start_time IS NOT NULL
        GROUP BY user_id, day
    )

    SELECT
        day,
        AVG(plays) AS "sprint_runs_per_user"
    FROM data
    GROUP BY day
    '''

    queries['avg_user_finished_plays'] = '''
    WITH data AS (
        SELECT user_id,
        DATE(start_time) AS day,
        COUNT(*) AS plays
        FROM sprint_runs
        WHERE user_id IS NOT NULL AND finished
        GROUP BY user_id, day
    )

    SELECT
        day,
        AVG(plays) AS "finished_sprint_runs_per_user"
    FROM data
    GROUP BY day
    '''
    
    queries['avg_user_lobby_plays'] = '''
    WITH data AS (
        SELECT user_id,
        DATE(start_time) AS day,
        COUNT(*) AS plays
        FROM lobby_runs
        WHERE user_id IS NOT NULL 
            AND start_time IS NOT NULL
        GROUP BY user_id, day
    )

    SELECT
        day,
        AVG(plays) AS "lobby_runs_per_user"
    FROM data
    GROUP BY day
    '''

    queries['avg_user_finished_lobby_plays'] = '''
    WITH data AS (
        SELECT user_id,
        DATE(start_time) AS day,
        COUNT(*) AS plays
        FROM lobby_runs
        WHERE user_id IS NOT NULL AND finished
        GROUP BY user_id, day
    )

    SELECT
        day,
        AVG(plays) AS "finished_lobby_runs_per_user"
    FROM data
    GROUP BY day
    '''

    queries['avg_user_quick_plays'] = '''
    WITH data AS (
        SELECT user_id,
        DATE(start_time) AS day,
        COUNT(*) AS plays
        FROM quick_runs
        WHERE user_id IS NOT NULL AND start_time IS NOT NULL
        GROUP BY user_id, day
    )

    SELECT
        day,
        AVG(plays) AS "quick_runs_per_user"
    FROM data
    GROUP BY day
    '''

    queries['avg_user_finished_quick_plays'] = '''
    WITH data AS (
        SELECT user_id,
        DATE(start_time) AS day,
        COUNT(*) AS plays
        FROM quick_runs
        WHERE user_id IS NOT NULL AND finished
        GROUP BY user_id, day
    )

    SELECT
        day,
        AVG(plays) AS "finished_quick_runs_per_user"
    FROM data
    GROUP BY day
    '''

    queries['active_users'] = '''
    WITH data AS (
        SELECT
            COUNT(*) AS plays,
            DATE(end_time) AS day,
            user_id
        FROM sprint_runs
        WHERE user_id IS NOT NULL AND finished
        GROUP BY user_id, day
    )

    SELECT 
        day,
        COUNT(*) AS active_users
    FROM data
    GROUP BY day
    '''
    
    queries['active_lobby_users'] = '''
    WITH data AS (
        SELECT
            COUNT(*) AS plays,
            DATE(end_time) AS day,
            user_id
        FROM lobby_runs
        WHERE user_id IS NOT NULL AND finished
        GROUP BY user_id, day
    )

    SELECT 
        day,
        COUNT(*) AS active_users
    FROM data
    GROUP BY day
    '''

    queries['active_quick_run_users'] = '''
    WITH data AS (
        SELECT
            COUNT(*) AS plays,
            DATE(end_time) AS day,
            user_id
        FROM quick_runs
        WHERE user_id IS NOT NULL AND finished
        GROUP BY user_id, day
    )

    SELECT 
        day,
        COUNT(*) AS active_quick_run_users
    FROM data
    GROUP BY day
    '''


    results = {} 

    db = get_db()
    with db.cursor(cursor=DictCursor) as cursor:
        for name, query in queries.items():
            cursor.execute(query)
            results[name] = cursor.fetchall()
    
    return results