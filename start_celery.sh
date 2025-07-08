#!/bin/bash

# Celery startup script for VectorCraft

# Check if Redis is running
echo "Checking Redis connection..."
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Redis is not running. Please start Redis first."
    echo "You can start Redis with: redis-server"
    exit 1
fi

echo "Redis is running ✓"

# Set environment variables
export CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://localhost:6379/0}
export CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://localhost:6379/0}

# Create log directory
mkdir -p logs

# Function to start Celery worker
start_worker() {
    echo "Starting Celery worker..."
    celery -A vectorization_tasks worker \
        --loglevel=info \
        --concurrency=4 \
        --max-tasks-per-child=100 \
        --logfile=logs/celery_worker.log \
        --pidfile=logs/celery_worker.pid \
        --queues=vectorization,batch_processing,image_analysis,maintenance \
        --hostname=worker@%h \
        --without-gossip \
        --without-mingle \
        --without-heartbeat \
        --detach
    
    if [ $? -eq 0 ]; then
        echo "Celery worker started successfully ✓"
    else
        echo "Failed to start Celery worker ✗"
        exit 1
    fi
}

# Function to start Celery beat scheduler
start_beat() {
    echo "Starting Celery beat scheduler..."
    celery -A vectorization_tasks beat \
        --loglevel=info \
        --logfile=logs/celery_beat.log \
        --pidfile=logs/celery_beat.pid \
        --schedule=logs/celerybeat-schedule \
        --detach
    
    if [ $? -eq 0 ]; then
        echo "Celery beat scheduler started successfully ✓"
    else
        echo "Failed to start Celery beat scheduler ✗"
        exit 1
    fi
}

# Function to start Flower monitoring
start_flower() {
    echo "Starting Flower monitoring..."
    celery -A vectorization_tasks flower \
        --address=0.0.0.0 \
        --port=5555 \
        --loglevel=info \
        --logfile=logs/flower.log \
        --pidfile=logs/flower.pid \
        --persistent=True \
        --db=logs/flower.db \
        --detach
    
    if [ $? -eq 0 ]; then
        echo "Flower monitoring started successfully ✓"
        echo "Flower UI available at: http://localhost:5555"
    else
        echo "Failed to start Flower monitoring ✗"
        exit 1
    fi
}

# Function to stop all Celery processes
stop_celery() {
    echo "Stopping Celery processes..."
    
    # Stop worker
    if [ -f logs/celery_worker.pid ]; then
        PID=$(cat logs/celery_worker.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "Celery worker stopped"
        fi
        rm -f logs/celery_worker.pid
    fi
    
    # Stop beat
    if [ -f logs/celery_beat.pid ]; then
        PID=$(cat logs/celery_beat.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "Celery beat stopped"
        fi
        rm -f logs/celery_beat.pid
    fi
    
    # Stop flower
    if [ -f logs/flower.pid ]; then
        PID=$(cat logs/flower.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "Flower stopped"
        fi
        rm -f logs/flower.pid
    fi
    
    echo "All Celery processes stopped ✓"
}

# Function to check status
check_status() {
    echo "Checking Celery status..."
    
    # Check worker
    if [ -f logs/celery_worker.pid ]; then
        PID=$(cat logs/celery_worker.pid)
        if kill -0 $PID 2>/dev/null; then
            echo "Celery worker: RUNNING (PID: $PID)"
        else
            echo "Celery worker: STOPPED"
        fi
    else
        echo "Celery worker: STOPPED"
    fi
    
    # Check beat
    if [ -f logs/celery_beat.pid ]; then
        PID=$(cat logs/celery_beat.pid)
        if kill -0 $PID 2>/dev/null; then
            echo "Celery beat: RUNNING (PID: $PID)"
        else
            echo "Celery beat: STOPPED"
        fi
    else
        echo "Celery beat: STOPPED"
    fi
    
    # Check flower
    if [ -f logs/flower.pid ]; then
        PID=$(cat logs/flower.pid)
        if kill -0 $PID 2>/dev/null; then
            echo "Flower: RUNNING (PID: $PID)"
        else
            echo "Flower: STOPPED"
        fi
    else
        echo "Flower: STOPPED"
    fi
}

# Function to show logs
show_logs() {
    case $1 in
        worker)
            if [ -f logs/celery_worker.log ]; then
                tail -f logs/celery_worker.log
            else
                echo "Worker log not found"
            fi
            ;;
        beat)
            if [ -f logs/celery_beat.log ]; then
                tail -f logs/celery_beat.log
            else
                echo "Beat log not found"
            fi
            ;;
        flower)
            if [ -f logs/flower.log ]; then
                tail -f logs/flower.log
            else
                echo "Flower log not found"
            fi
            ;;
        *)
            echo "Available logs: worker, beat, flower"
            ;;
    esac
}

# Function to restart services
restart_celery() {
    echo "Restarting Celery services..."
    stop_celery
    sleep 2
    start_worker
    start_beat
    start_flower
}

# Function to purge all tasks
purge_tasks() {
    echo "Purging all tasks..."
    celery -A vectorization_tasks purge -f
    echo "All tasks purged ✓"
}

# Function to show help
show_help() {
    echo "Usage: $0 {start|stop|restart|status|logs|purge|help}"
    echo ""
    echo "Commands:"
    echo "  start    Start Celery worker, beat, and flower"
    echo "  stop     Stop all Celery processes"
    echo "  restart  Restart all Celery processes"
    echo "  status   Check status of Celery processes"
    echo "  logs     Show logs (worker|beat|flower)"
    echo "  purge    Purge all tasks from queues"
    echo "  help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start          # Start all services"
    echo "  $0 logs worker    # Show worker logs"
    echo "  $0 status         # Check status"
}

# Main script logic
case $1 in
    start)
        start_worker
        start_beat
        start_flower
        check_status
        ;;
    stop)
        stop_celery
        ;;
    restart)
        restart_celery
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs $2
        ;;
    purge)
        purge_tasks
        ;;
    help)
        show_help
        ;;
    *)
        echo "Error: Invalid command"
        show_help
        exit 1
        ;;
esac