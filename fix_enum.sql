-- Fix PlanStatus enum to add new values
-- Run this SQL directly in PostgreSQL

-- Check current enum values
SELECT unnest(enum_range(NULL::planstatus))::text as current_values;

-- Add new enum values
ALTER TYPE planstatus ADD VALUE IF NOT EXISTS 'COMPLETED_WON';
ALTER TYPE planstatus ADD VALUE IF NOT EXISTS 'COMPLETED_FULL';

-- Verify the update
SELECT unnest(enum_range(NULL::planstatus))::text as updated_values;

-- You should now see:
-- ACTIVE
-- COMPLETED
-- CANCELLED
-- COMPLETED_WON
-- COMPLETED_FULL
