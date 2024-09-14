from flask_restful import Resource
from rq import Queue, Connection
from auth.accesscontrol import AllowedRoles, handle_exception_pretty, roles_required
from helpers.redis_commands import conn as redis_connection
from tasks.generate_documents_task import calculate_progress, get_notification
from helpers.logger import app_logger

class TaskProgressStatus(Resource):
    @classmethod
    @handle_exception_pretty
    @roles_required([AllowedRoles.admin.name, AllowedRoles.program_manager.name])
    def get(cls, task_id):
        with Connection(redis_connection):
            q = Queue()
            create_task = q.fetch_job(task_id)
            progress = calculate_progress(create_task)
            notification = get_notification(create_task)
            if create_task:
                if create_task.is_failed:
                    return {
                               'progress': progress,
                               'message': "Task failed to finish"
                           }, 500
                if create_task.is_finished:
                    app_logger.info(notification)
                    if isinstance(create_task.result, str):
                        return {
                               'progress': -1,
                               'notification': notification,
                               'message': create_task.result
                           }, 200
                    return {
                               'progress': progress,
                               'notification': notification,
                               'documents': [str(res) for res in create_task.result]
                           }, 200
                else:
                    return {
                               'progress': progress
                           }, 200
        return {
                   'progress': -1,
                   'message': 'Task does not exists or already finished'
               }, 500
