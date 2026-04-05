-- PostXG Database Schema
-- Created: 2026-04-07
-- Database: Supabase PostgreSQL (us-east-1)

-- Table 1: Pipeline Runs (main logging table)
CREATE TABLE pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed', 'failed')),
    interface TEXT NOT NULL CHECK (interface IN ('terminal', 'telegram', 'streamlit')),
    
    -- Input metadata
    input_sources_count INTEGER,
    grok_used BOOLEAN DEFAULT FALSE,
    youtube_count INTEGER DEFAULT 0,
    manual_count INTEGER DEFAULT 0,
    
    -- Router classification
    content_type TEXT CHECK (content_type IN ('match_result', 'transfer_news', 'tactical_analysis', 'unknown')),
    router_confidence INTEGER CHECK (router_confidence >= 0 AND router_confidence <= 100),
    router_reasoning TEXT,
    
    -- Model usage & cost - Extraction
    extraction_model TEXT,
    extraction_tokens_in INTEGER,
    extraction_tokens_out INTEGER,
    extraction_cost_usd DECIMAL(10,6),
    
    -- Model usage & cost - Brief generation
    brief_model TEXT,
    brief_tokens_in INTEGER,
    brief_tokens_out INTEGER,
    brief_cost_usd DECIMAL(10,6),
    
    -- Model usage & cost - Grok
    grok_cost_usd DECIMAL(10,6),
    
    -- Total cost
    total_cost_usd DECIMAL(10,6),
    
    -- Output metadata
    format_type TEXT CHECK (format_type IN ('short', 'long', 'both')),
    output_length_chars INTEGER,
    output_length_words INTEGER,
    brief_output TEXT,
    
    -- User context
    user_direction TEXT,
    strongest_angle TEXT,
    
    -- YouTube linking
    youtube_video_id TEXT,
    youtube_video_url TEXT,
    published_at TIMESTAMPTZ,
    video_linked BOOLEAN DEFAULT FALSE
);

-- Table 2: Eval Results (quality scoring)
CREATE TABLE eval_results (
    eval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Eval model usage
    eval_model TEXT,
    eval_tokens_in INTEGER,
    eval_tokens_out INTEGER,
    eval_cost_usd DECIMAL(10,6),
    
    -- Eval scores
    accuracy_score INTEGER CHECK (accuracy_score >= 0 AND accuracy_score <= 100),
    relevance_score INTEGER CHECK (relevance_score >= 0 AND relevance_score <= 100),
    hallucination_risk TEXT CHECK (hallucination_risk IN ('low', 'medium', 'high')),
    passed BOOLEAN NOT NULL,
    
    -- Eval feedback
    flagged_claims TEXT[],
    eval_reasoning TEXT
);

-- Table 3: YouTube Video Performance (daily snapshots)
CREATE TABLE youtube_video_performance (
    performance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    video_id TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    
    -- Core metrics
    views INTEGER DEFAULT 0,
    watch_time_minutes INTEGER DEFAULT 0,
    avg_view_duration_seconds INTEGER DEFAULT 0,
    avg_percentage_viewed DECIMAL(5,2),
    
    -- Engagement
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    subscribers_gained INTEGER DEFAULT 0,
    
    -- Traffic
    impressions INTEGER DEFAULT 0,
    click_through_rate DECIMAL(5,2),
    
    -- Revenue
    estimated_revenue_usd DECIMAL(10,2),
    
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure one snapshot per day per video
    UNIQUE(video_id, snapshot_date)
);

-- Table 4: Video Transcripts (analyze brief vs actual script)
CREATE TABLE video_transcripts (
    transcript_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    video_id TEXT NOT NULL UNIQUE,
    
    -- Raw transcript
    transcript_text TEXT NOT NULL,
    transcript_fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Metadata
    video_duration_seconds INTEGER,
    word_count INTEGER,
    speaking_rate_wpm DECIMAL(5,2),
    
    -- Brief adherence analysis
    brief_adherence_score INTEGER CHECK (brief_adherence_score >= 0 AND brief_adherence_score <= 100),
    topics_covered TEXT[],
    topics_skipped TEXT[],
    ad_libbed_content TEXT[],
    
    -- Sentiment analysis
    dominant_sentiment TEXT CHECK (dominant_sentiment IN ('analytical', 'frustrated', 'excited', 'sarcastic', 'neutral')),
    emotional_words_count INTEGER,
    emotional_language_examples TEXT[],
    
    analyzed_at TIMESTAMPTZ
);

-- Indexes for performance optimization
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);
CREATE INDEX idx_pipeline_runs_content_type ON pipeline_runs(content_type);
CREATE INDEX idx_pipeline_runs_video_linked ON pipeline_runs(video_linked);
CREATE INDEX idx_eval_results_run_id ON eval_results(run_id);
CREATE INDEX idx_youtube_performance_run_id ON youtube_video_performance(run_id);
CREATE INDEX idx_youtube_performance_video_id ON youtube_video_performance(video_id);
CREATE INDEX idx_youtube_performance_snapshot_date ON youtube_video_performance(snapshot_date DESC);
CREATE INDEX idx_video_transcripts_run_id ON video_transcripts(run_id);
CREATE INDEX idx_video_transcripts_video_id ON video_transcripts(video_id);
CREATE INDEX idx_video_transcripts_brief_adherence ON video_transcripts(brief_adherence_score);
CREATE INDEX idx_video_transcripts_fetched_at ON video_transcripts(transcript_fetched_at DESC);
