-- ============================================================
-- Database Schema for Campus Resource Optimizer
-- BCA (AI & Data Science) College Project
-- ============================================================

-- Step 1: Create Database
DROP DATABASE IF EXISTS campus_optimizer;
CREATE DATABASE campus_optimizer;
USE campus_optimizer;

-- Step 2: Create 'resources' Table
CREATE TABLE resources (
    resource_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    resource_type ENUM('Classroom', 'Computer Lab', 'Seminar Hall', 'Auditorium') NOT NULL,
    capacity INT NOT NULL,
    building VARCHAR(100) NOT NULL,
    floor INT NOT NULL,
    equipment VARCHAR(255) DEFAULT 'None',
    status ENUM('Available', 'Unavailable') NOT NULL DEFAULT 'Available'
);

-- Step 3: Create 'bookings' Table
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    resource_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    student_count INT NOT NULL,
    purpose VARCHAR(255) DEFAULT 'General',
    status ENUM('Confirmed', 'Cancelled') NOT NULL DEFAULT 'Confirmed',
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE
);

-- Step 4: Insert Sample Campus Resources
INSERT INTO resources (resource_id, name, resource_type, capacity, building, floor, equipment, status) VALUES
('A-101', 'Classroom A-101', 'Classroom', 60, 'Academic Block', 1, 'Projector, AC', 'Available'),
('A-102', 'Classroom A-102', 'Classroom', 50, 'Academic Block', 1, 'Projector', 'Available'),
('A-105', 'Classroom A-105', 'Classroom', 55, 'Academic Block', 2, 'Projector, Smart Board', 'Available'),
('B-201', 'Classroom B-201', 'Classroom', 70, 'Science Block', 2, 'Projector, Sound System', 'Available'),
('LAB-01', 'Computer Lab 01', 'Computer Lab', 40, 'Computer Block', 2, '40 Computers, AC, Projector', 'Available'),
('LAB-02', 'Computer Lab 02', 'Computer Lab', 45, 'Computer Block', 2, '45 Computers, AC', 'Available'),
('SH-01', 'Seminar Hall 01', 'Seminar Hall', 150, 'Main Block', 0, 'Projector, Sound System, AC', 'Available'),
('AUD-01', 'Main Auditorium', 'Auditorium', 300, 'Main Block', 0, 'Projector, Sound System, Stage, AC', 'Available');

-- Step 5: Insert Sample Bookings for Testing Conflict Detection
INSERT INTO bookings (resource_id, date, start_time, end_time, student_count, purpose, status) VALUES
('A-101', '2026-10-10', '10:00:00', '11:00:00', 55, 'AI & DS Lecture', 'Confirmed'),
('LAB-01', '2026-10-10', '14:00:00', '16:00:00', 35, 'Python Programming Lab', 'Confirmed'),
('SH-01', '2026-10-12', '09:30:00', '12:30:00', 130, 'Guest Lecture on Machine Learning', 'Confirmed');
