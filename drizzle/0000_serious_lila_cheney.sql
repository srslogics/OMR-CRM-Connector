CREATE TABLE `members` (
	`email` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`user_id` text,
	`active` integer DEFAULT 1 NOT NULL
);
--> statement-breakpoint
CREATE TABLE `ownership` (
	`id` integer PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`email` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `records` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`school` text NOT NULL,
	`father_phone` text NOT NULL,
	`mother_phone` text NOT NULL,
	`class_name` text NOT NULL,
	`submitter_id` text NOT NULL,
	`submitter_email` text NOT NULL,
	`status` text DEFAULT 'New' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_records_submitter` ON `records` (`submitter_id`);--> statement-breakpoint
CREATE INDEX `idx_records_created` ON `records` (`created_at`);