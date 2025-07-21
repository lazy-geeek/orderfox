-- Migration script to add is_paper_trading column to bots table
-- Run this script manually in production environment

ALTER TABLE bots 
ADD COLUMN is_paper_trading BOOLEAN NOT NULL DEFAULT TRUE;

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'bots' AND column_name = 'is_paper_trading';