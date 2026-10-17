"""
app.py - Main Flask Application
Campus Resource Optimizer - BCA (AI & DS) College Project

This web application helps college faculty and administrators:
1. Manage campus resources (Classrooms, Labs, Seminar Halls, Auditoriums)
2. View real-time availability and capacity
3. Book resources with automatic time-conflict detection
4. Recommend the most optimal resource using basic DSA (Searching & Sorting)
"""

import os
from collections import deque
from datetime import datetime, time
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from dotenv import load_dotenv
from database import get_db_connection

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Secret key for session management and flash messages
app.secret_key = os.getenv('SECRET_KEY', 'campus_resource_optimizer_secret_2026')


# ==============================================================================
# DSA DATA STRUCTURE: QUEUE (FIFO)
# ==============================================================================
# We use Python's collections.deque as a simple Queue to track recent booking
# operations in First-In-First-Out order (max 10 items).
# This demonstrates DSA: Queue operations (enqueue with append, dequeue with popleft).
booking_activity_queue = deque(maxlen=10)


# ==============================================================================
# HELPER FUNCTIONS & DATABASE OPERATIONS
# ==============================================================================

def get_resources(resource_type=None, min_capacity=None, building=None, status=None, sort_by=None):
    """
    Fetch resources from the database with optional search filters and sorting.
    Demonstrates DSA:
    1. Searching / Filtering: Iterating and filtering datasets based on conditions.
    2. Sorting: Ordering data based on capacity, name, or availability.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM resources")
    resources = cursor.fetchall()
    cursor.close()
    conn.close()

    # --- DSA SEARCHING / FILTERING (In-Memory Filtering) ---
    filtered_resources = []
    for r in resources:
        # Check resource type filter
        if resource_type and resource_type != 'All' and r['resource_type'].lower() != resource_type.lower():
            continue
        # Check minimum capacity filter
        if min_capacity and r['capacity'] < int(min_capacity):
            continue
        # Check building filter
        if building and building != 'All' and r['building'].lower() != building.lower():
            continue
        # Check status filter
        if status and status != 'All' and r['status'].lower() != status.lower():
            continue
        
        filtered_resources.append(r)

    # --- DSA SORTING ---
    # Sort resources by selected field using Python's built-in Timsort (O(n log n))
    if sort_by == 'capacity_asc':
        filtered_resources.sort(key=lambda x: x['capacity'])
    elif sort_by == 'capacity_desc':
        filtered_resources.sort(key=lambda x: x['capacity'], reverse=True)
    elif sort_by == 'name':
        filtered_resources.sort(key=lambda x: x['name'].lower())
    elif sort_by == 'status':
        filtered_resources.sort(key=lambda x: x['status'])
    else:
        # Default sort by resource_id
        filtered_resources.sort(key=lambda x: x['resource_id'])

    return filtered_resources


def get_resource_dict():
    """
    Demonstrates DSA: Hash Table / Dictionary.
    Creates an O(1) fast lookup dictionary keyed by resource_id:
    { 'A-101': {'resource_id': 'A-101', 'name': 'Classroom A-101', ...}, ... }
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM resources")
    resources = cursor.fetchall()
    cursor.close()
    conn.close()

    # Build the Hash Map (Dictionary)
    resource_map = {r['resource_id']: r for r in resources}
    return resource_map


def get_resource(resource_id):
    """Fetch a single resource by its primary key."""
    # Demonstrating Hash Table lookup:
    resource_map = get_resource_dict()
    return resource_map.get(resource_id)


def add_resource(data):
    """Insert a new resource into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO resources (resource_id, name, resource_type, capacity, building, floor, equipment, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (
        data['resource_id'].strip().upper(),
        data['name'].strip(),
        data['resource_type'],
        int(data['capacity']),
        data['building'].strip(),
        int(data['floor']),
        data.get('equipment', 'None').strip(),
        data.get('status', 'Available')
    ))
    conn.commit()
    cursor.close()
    conn.close()


def update_resource(resource_id, data):
    """Update an existing resource."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        UPDATE resources
        SET name = %s, resource_type = %s, capacity = %s, building = %s, floor = %s, equipment = %s, status = %s
        WHERE resource_id = %s
    """
    cursor.execute(query, (
        data['name'].strip(),
        data['resource_type'],
        int(data['capacity']),
        data['building'].strip(),
        int(data['floor']),
        data.get('equipment', 'None').strip(),
        data.get('status', 'Available'),
        resource_id
    ))
    conn.commit()
    cursor.close()
    conn.close()


def delete_resource(resource_id):
    """Delete a resource by ID. Foreign key ON DELETE CASCADE cleans up bookings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM resources WHERE resource_id = %s", (resource_id,))
    conn.commit()
    cursor.close()
    conn.close()


def get_bookings():
    """Fetch all bookings along with resource names, ordered by date and start_time."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT b.booking_id, b.resource_id, b.date, b.start_time, b.end_time,
               b.student_count, b.purpose, b.status, r.name AS resource_name, r.capacity
        FROM bookings b
        JOIN resources r ON b.resource_id = r.resource_id
        ORDER BY b.date DESC, b.start_time DESC
    """
    cursor.execute(query)
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()

    # Format time and date cleanly for frontend display
    for b in bookings:
        if isinstance(b['date'], datetime) or hasattr(b['date'], 'strftime'):
            b['date_formatted'] = b['date'].strftime('%Y-%m-%d')
        else:
            b['date_formatted'] = str(b['date'])

        # Format start_time and end_time (handling timedelta from MySQL)
        b['start_formatted'] = str(b['start_time'])[:5]
        b['end_formatted'] = str(b['end_time'])[:5]

    return bookings


def check_availability(resource_id, date, new_start, new_end):
    """
    Check if a resource is available for the given time slot.
    Returns:
        (is_free, conflict_message)

    Time Overlap Logic:
    Two time intervals [Start1, End1) and [Start2, End2) overlap if:
        Start_New < End_Existing AND End_New > Start_Existing
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT booking_id, start_time, end_time, purpose
        FROM bookings
        WHERE resource_id = %s
          AND date = %s
          AND status = 'Confirmed'
          AND (start_time < %s AND end_time > %s)
    """
    cursor.execute(query, (resource_id, date, new_end, new_start))
    conflicts = cursor.fetchall()
    cursor.close()
    conn.close()

    if conflicts:
        conflict = conflicts[0]
        c_start = str(conflict['start_time'])[:5]
        c_end = str(conflict['end_time'])[:5]
        return False, f"Booking conflict: {resource_id} is already booked from {c_start} to {c_end}."

    return True, None


def add_booking(data):
    """Insert a new confirmed booking into MySQL."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO bookings (resource_id, date, start_time, end_time, student_count, purpose, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'Confirmed')
    """
    cursor.execute(query, (
        data['resource_id'],
        data['date'],
        data['start_time'],
        data['end_time'],
        int(data['student_count']),
        data.get('purpose', 'Class / Event').strip()
    ))
    conn.commit()
    cursor.close()
    conn.close()

    # Enqueue this booking action into our DSA Queue
    booking_activity_queue.append({
        'action': 'Booked',
        'resource_id': data['resource_id'],
        'time': datetime.now().strftime('%H:%M:%S'),
        'students': data['student_count']
    })


def cancel_booking(booking_id):
    """Cancel an existing booking."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET status = 'Cancelled' WHERE booking_id = %s", (booking_id,))
    conn.commit()
    cursor.close()
    conn.close()

    # Enqueue this cancellation into our DSA Queue
    booking_activity_queue.append({
        'action': 'Cancelled',
        'resource_id': f'Booking #{booking_id}',
        'time': datetime.now().strftime('%H:%M:%S'),
        'students': '-'
    })


def get_dashboard_stats():
    """
    Compute dynamic dashboard statistics directly from MySQL database:
    - Total Resources
    - Available Resources
    - Booked Resources
    - Total Bookings
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Total resources count
    cursor.execute("SELECT COUNT(*) AS total FROM resources")
    total_resources = cursor.fetchone()['total']

    # Available resources count
    cursor.execute("SELECT COUNT(*) AS available FROM resources WHERE status = 'Available'")
    available_resources = cursor.fetchone()['available']

    # Booked / Unavailable resources count
    cursor.execute("SELECT COUNT(*) AS booked FROM resources WHERE status = 'Unavailable'")
    booked_resources = cursor.fetchone()['booked']

    # Total bookings count
    cursor.execute("SELECT COUNT(*) AS total_bookings FROM bookings WHERE status = 'Confirmed'")
    total_bookings = cursor.fetchone()['total_bookings']

    cursor.close()
    conn.close()

    return {
        'total_resources': total_resources,
        'available_resources': available_resources,
        'booked_resources': booked_resources,
        'total_bookings': total_bookings
    }


def recommend_resource(student_count, resource_type, required_equipment):
    """
    Recommend the most optimal resource based on student capacity and requirements.
    
    DSA Steps:
    1. Filter resources matching resource_type (or all types).
    2. Filter out resources with insufficient capacity (capacity < student_count).
    3. Filter out resources marked as 'Unavailable'.
    4. Check equipment match (checks if requested equipment is included in resource equipment).
    5. Sorting (DSA): Sort candidates by capacity difference (capacity - student_count) ascending.
       This ensures optimal space utilization (e.g. 50 students assigned to 60-seat room, not 300-seat auditorium).
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM resources WHERE status = 'Available'")
    all_available = cursor.fetchall()
    cursor.close()
    conn.close()

    # 1. Filter by type & capacity
    suitable_candidates = []
    for r in all_available:
        if resource_type and resource_type != 'All' and r['resource_type'].lower() != resource_type.lower():
            continue
        if r['capacity'] < student_count:
            continue
        suitable_candidates.append(r)

    if not suitable_candidates:
        return None, [], "No available resource has sufficient capacity for this request."

    # 2. Check Equipment Requirement
    req_equip = [e.strip().lower() for e in required_equipment.split(',') if e.strip()] if required_equipment else []

    matches_with_equipment = []
    matches_without_equipment = []

    for r in suitable_candidates:
        r_equip_lower = (r['equipment'] or '').lower()
        # Check if all requested equipments are present in the room's equipment list
        has_all_equipment = all(equip in r_equip_lower for equip in req_equip)
        if has_all_equipment:
            matches_with_equipment.append(r)
        else:
            matches_without_equipment.append(r)

    # DSA Sorting: Sort candidate rooms by closest capacity to minimize wasted seats
    # Key: (capacity - student_count)
    if matches_with_equipment:
        matches_with_equipment.sort(key=lambda r: (r['capacity'] - student_count))
        best_resource = matches_with_equipment[0]
        other_suitable = matches_with_equipment[1:] + matches_without_equipment
        reason = "Capacity is sufficient, all requested equipment is available, and room status is Available."
    else:
        # If no room has all requested equipment, recommend the best room by capacity
        matches_without_equipment.sort(key=lambda r: (r['capacity'] - student_count))
        best_resource = matches_without_equipment[0]
        other_suitable = matches_without_equipment[1:]
        reason = "Capacity is sufficient and room is Available (Note: Some requested equipment may be missing)."

    return best_resource, other_suitable, reason


# ==============================================================================
# FLASK WEB ROUTES
# ==============================================================================

@app.route('/')
def dashboard():
    """Home / Dashboard page displaying live statistics and quick actions."""
    try:
        stats = get_dashboard_stats()
    except Exception as e:
        stats = {'total_resources': 0, 'available_resources': 0, 'booked_resources': 0, 'total_bookings': 0}
        flash(f"Database connection warning: {e}", "danger")

    recent_activities = list(booking_activity_queue)
    return render_template('index.html', stats=stats, recent_activities=recent_activities)


@app.route('/resources', methods=['GET'])
def resources_page():
    """
    Resources management page:
    - View all resources in a clean table
    - Search & filter by Type, Min Capacity, Building, Status
    - Sort resources by Capacity, Name, Status (DSA Sorting)
    """
    # Read search & filter parameters from query string
    r_type = request.args.get('resource_type', '')
    min_cap = request.args.get('min_capacity', '')
    building = request.args.get('building', '')
    status = request.args.get('status', '')
    sort_by = request.args.get('sort_by', '')

    min_cap_int = int(min_cap) if min_cap.isdigit() else None

    try:
        resources = get_resources(
            resource_type=r_type,
            min_capacity=min_cap_int,
            building=building,
            status=status,
            sort_by=sort_by
        )
    except Exception as e:
        resources = []
        flash(f"Error fetching resources: {e}", "danger")

    return render_template(
        'resources.html',
        resources=resources,
        selected_type=r_type,
        selected_min_cap=min_cap,
        selected_building=building,
        selected_status=status,
        selected_sort=sort_by
    )


@app.route('/resources/add', methods=['POST'])
def add_resource_route():
    """Add a new campus resource."""
    try:
        # Check if resource_id already exists (DSA Dictionary Lookup)
        resource_id = request.form.get('resource_id', '').strip().upper()
        if not resource_id:
            flash("Resource ID is required.", "danger")
            return redirect(url_for('resources_page'))

        if get_resource(resource_id):
            flash(f"Resource with ID '{resource_id}' already exists!", "danger")
            return redirect(url_for('resources_page'))

        add_resource(request.form)
        flash(f"Resource '{resource_id}' successfully added!", "success")
    except Exception as e:
        flash(f"Error adding resource: {e}", "danger")

    return redirect(url_for('resources_page'))


@app.route('/resources/edit/<resource_id>', methods=['POST'])
def edit_resource_route(resource_id):
    """Update an existing campus resource."""
    try:
        update_resource(resource_id, request.form)
        flash(f"Resource '{resource_id}' successfully updated!", "success")
    except Exception as e:
        flash(f"Error updating resource: {e}", "danger")

    return redirect(url_for('resources_page'))


@app.route('/resources/delete/<resource_id>', methods=['POST'])
def delete_resource_route(resource_id):
    """Delete a resource by ID."""
    try:
        delete_resource(resource_id)
        flash(f"Resource '{resource_id}' deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting resource: {e}", "danger")

    return redirect(url_for('resources_page'))


@app.route('/bookings', methods=['GET'])
def bookings_page():
    """
    Bookings page:
    - View booking form
    - View existing bookings table with statuses
    - Optional pre-filling for resource_id from recommendation page
    """
    prefill_resource = request.args.get('resource_id', '')
    prefill_students = request.args.get('students', '')

    try:
        bookings = get_bookings()
        resources = get_resources()
    except Exception as e:
        bookings = []
        resources = []
        flash(f"Error loading bookings: {e}", "danger")

    return render_template(
        'bookings.html',
        bookings=bookings,
        resources=resources,
        prefill_resource=prefill_resource,
        prefill_students=prefill_students
    )


@app.route('/bookings/add', methods=['POST'])
def add_booking_route():
    """
    Process new booking with complete verification:
    1. Check resource existence
    2. Check capacity (student_count <= capacity)
    3. Check start_time < end_time
    4. Check for time overlap conflict
    5. Save booking and display appropriate message
    """
    resource_id = request.form.get('resource_id', '').strip()
    booking_date = request.form.get('date', '').strip()
    start_time = request.form.get('start_time', '').strip()
    end_time = request.form.get('end_time', '').strip()
    student_count_raw = request.form.get('student_count', '0')
    purpose = request.form.get('purpose', '').strip()

    try:
        student_count = int(student_count_raw)
    except ValueError:
        flash("Invalid student count.", "danger")
        return redirect(url_for('bookings_page'))

    # Step 1: Check resource existence (DSA Hash Map lookup)
    resource = get_resource(resource_id)
    if not resource:
        flash(f"Resource '{resource_id}' does not exist.", "danger")
        return redirect(url_for('bookings_page'))

    # Step 2: Check resource status
    if resource['status'] == 'Unavailable':
        flash(f"Resource '{resource_id}' is marked as Unavailable / Maintenance.", "danger")
        return redirect(url_for('bookings_page'))

    # Step 3: Check room capacity
    if student_count > resource['capacity']:
        flash(f"Capacity exceeded: {resource_id} can only accommodate {resource['capacity']} students (requested {student_count}).", "danger")
        return redirect(url_for('bookings_page'))

    # Step 4: Validate time sequence
    if start_time >= end_time:
        flash("Invalid time: Start time must be earlier than End time.", "danger")
        return redirect(url_for('bookings_page'))

    # Step 5: Conflict Detection (Check time overlap in database)
    is_available, conflict_msg = check_availability(resource_id, booking_date, start_time, end_time)
    if not is_available:
        flash(conflict_msg, "danger")
        return redirect(url_for('bookings_page'))

    # Step 6: Save Booking
    try:
        add_booking({
            'resource_id': resource_id,
            'date': booking_date,
            'start_time': start_time,
            'end_time': end_time,
            'student_count': student_count,
            'purpose': purpose
        })
        flash(f"Booking successful! {resource['name']} ({resource_id}) reserved for {booking_date} ({start_time} - {end_time}).", "success")
    except Exception as e:
        flash(f"Failed to save booking: {e}", "danger")

    return redirect(url_for('bookings_page'))


@app.route('/bookings/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking_route(booking_id):
    """Cancel an active booking."""
    try:
        cancel_booking(booking_id)
        flash(f"Booking #{booking_id} cancelled.", "info")
    except Exception as e:
        flash(f"Error cancelling booking: {e}", "danger")

    return redirect(url_for('bookings_page'))


@app.route('/recommendation', methods=['GET', 'POST'])
def recommendation_page():
    """
    Recommendation page:
    - User inputs: student count, resource type, required equipment
    - Returns best matching resource + other suitable candidates
    """
    recommended = None
    other_suitable = []
    reason = None
    searched = False
    students = ""
    resource_type = ""
    equipment = ""

    if request.method == 'POST':
        searched = True
        students_raw = request.form.get('students', '0')
        resource_type = request.form.get('resource_type', 'All')
        equipment = request.form.get('equipment', '').strip()

        try:
            student_count = int(students_raw)
            students = student_count
            recommended, other_suitable, reason = recommend_resource(student_count, resource_type, equipment)
        except ValueError:
            flash("Please enter a valid number of students.", "danger")
        except Exception as e:
            flash(f"Error finding recommendation: {e}", "danger")

    return render_template(
        'recommendation.html',
        searched=searched,
        recommended=recommended,
        other_suitable=other_suitable,
        reason=reason,
        students=students,
        resource_type=resource_type,
        equipment=equipment
    )


@app.route('/download-zip')
def download_zip():
    """Endpoint allowing 1-click download of the complete project as a ZIP archive."""
    zip_path = os.path.join(os.path.dirname(__file__), 'campus-resource-optimizer.zip')
    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True, download_name='campus-resource-optimizer.zip')
    flash("Project ZIP archive not found on server.", "warning")
    return redirect(url_for('dashboard'))


# ==============================================================================
# MAIN APPLICATION ENTRY POINT
# ==============================================================================
if __name__ == '__main__':
    # Running Flask development server on port 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
