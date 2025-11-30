import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, jsonb, integer, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";
import { relations } from "drizzle-orm";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  email: varchar("email").unique(),
  firstName: varchar("first_name"),
  lastName: varchar("last_name"), 
  profileImageUrl: varchar("profile_image_url"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const uploadedFiles = pgTable("uploaded_files", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").references(() => users.id).notNull(),
  fileName: text("file_name").notNull(),
  originalName: text("original_name").notNull(),
  mimeType: text("mime_type").notNull(),
  fileSize: integer("file_size").notNull(),
  fileUrl: text("file_url"),
  uploadedAt: timestamp("uploaded_at").defaultNow().notNull(),
});

export const comparisons = pgTable("comparisons", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").references(() => users.id).notNull(),
  baselineFileId: varchar("baseline_file_id").references(() => uploadedFiles.id).notNull(),
  revisedFileId: varchar("revised_file_id").references(() => uploadedFiles.id).notNull(),
  baselineOriginalName: text("baseline_original_name"),
  revisedOriginalName: text("revised_original_name"),
  drawingNumber: text("drawing_number"),
  autoDetectedDrawingNumber: boolean("auto_detected_drawing_number").default(false),
  status: text("status").notNull().default("pending"),
  allPagesReady: boolean("all_pages_ready").default(false),
  kpis: jsonb("kpis").$type<{
    added: number;
    modified: number;
    removed: number;
  }>(),
  changes: jsonb("changes").$type<any[]>(),
  pageInfo: jsonb("page_info").$type<{ added: number; modified: number; removed: number }>(),
  pageMapping: jsonb("page_mapping").$type<Array<[string, number, number]>>(),
  openaiThreads: jsonb("openai_threads").$type<Record<string, string>>(),
  analysisSummary: text("analysis_summary"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const usersRelations = relations(users, ({ many }) => ({
  uploadedFiles: many(uploadedFiles),
  comparisons: many(comparisons),
}));

export const uploadedFilesRelations = relations(uploadedFiles, ({ one, many }) => ({
  user: one(users, {
    fields: [uploadedFiles.userId],
    references: [users.id],
  }),
  baselineComparisons: many(comparisons, { relationName: "baselineFile" }),
  revisedComparisons: many(comparisons, { relationName: "revisedFile" }),
}));

export const comparisonsRelations = relations(comparisons, ({ one }) => ({
  user: one(users, {
    fields: [comparisons.userId],
    references: [users.id],
  }),
  baselineFile: one(uploadedFiles, {
    fields: [comparisons.baselineFileId],
    references: [uploadedFiles.id],
    relationName: "baselineFile",
  }),
  revisedFile: one(uploadedFiles, {
    fields: [comparisons.revisedFileId],
    references: [uploadedFiles.id],
    relationName: "revisedFile",
  }),
}));

export const upsertUserSchema = createInsertSchema(users).omit({
  createdAt: true,
  updatedAt: true,
});

export const insertUploadedFileSchema = createInsertSchema(uploadedFiles).omit({
  id: true,
  uploadedAt: true,
});

export const insertComparisonSchema = createInsertSchema(comparisons).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type UpsertUser = z.infer<typeof upsertUserSchema>;
export type User = typeof users.$inferSelect;
export type InsertUploadedFile = z.infer<typeof insertUploadedFileSchema>;
export type UploadedFile = typeof uploadedFiles.$inferSelect;
export type InsertComparison = z.infer<typeof insertComparisonSchema>;
export type Comparison = typeof comparisons.$inferSelect;
