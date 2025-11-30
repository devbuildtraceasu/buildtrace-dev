import { 
  users,
  uploadedFiles, 
  comparisons,
  type User, 
  type UpsertUser, 
  type UploadedFile,
  type InsertUploadedFile,
  type Comparison, 
  type InsertComparison 
} from "@shared/schema";
import { db } from "./db";
import { eq, and } from "drizzle-orm";
import { randomUUID } from "crypto";

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  upsertUser(user: UpsertUser): Promise<User>;
  
  // File operations
  createUploadedFile(file: InsertUploadedFile): Promise<UploadedFile>;
  getUploadedFile(id: string): Promise<UploadedFile | undefined>;
  getUserUploadedFiles(userId: string): Promise<UploadedFile[]>;
  updateUploadedFile(id: string, updates: Partial<UploadedFile>): Promise<UploadedFile | undefined>;
  deleteUploadedFile(id: string): Promise<boolean>;
  
  // Comparison methods
  getComparison(id: string): Promise<Comparison | undefined>;
  getUserComparisons(userId: string): Promise<Comparison[]>;
  createComparison(comparison: InsertComparison): Promise<Comparison>;
  updateComparison(id: string, updates: Partial<Comparison>): Promise<Comparison | undefined>;
  deleteComparison(id: string): Promise<boolean>;
}

// Database storage implementation
export class DatabaseStorage implements IStorage {
  async getUser(id: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user;
  }

  async upsertUser(userData: UpsertUser): Promise<User> {
    const [user] = await db
      .insert(users)
      .values(userData)
      .onConflictDoUpdate({
        target: users.id,
        set: {
          ...userData,
          updatedAt: new Date(),
        },
      })
      .returning();
    return user;
  }

  // File operations
  async createUploadedFile(fileData: InsertUploadedFile): Promise<UploadedFile> {
    const [file] = await db
      .insert(uploadedFiles)
      .values(fileData)
      .returning();
    return file;
  }

  async getUploadedFile(id: string): Promise<UploadedFile | undefined> {
    const [file] = await db.select().from(uploadedFiles).where(eq(uploadedFiles.id, id));
    return file;
  }

  async getUserUploadedFiles(userId: string): Promise<UploadedFile[]> {
    return await db.select().from(uploadedFiles).where(eq(uploadedFiles.userId, userId));
  }

  async updateUploadedFile(id: string, updates: Partial<UploadedFile>): Promise<UploadedFile | undefined> {
    const [file] = await db
      .update(uploadedFiles)
      .set(updates)
      .where(eq(uploadedFiles.id, id))
      .returning();
    return file;
  }

  async deleteUploadedFile(id: string): Promise<boolean> {
    const result = await db.delete(uploadedFiles).where(eq(uploadedFiles.id, id));
    return (result.rowCount ?? 0) > 0;
  }

  // Comparison operations
  async getComparison(id: string): Promise<Comparison | undefined> {
    const [comparison] = await db.select().from(comparisons).where(eq(comparisons.id, id));
    return comparison;
  }

  async getUserComparisons(userId: string): Promise<Comparison[]> {
    return await db.select().from(comparisons).where(eq(comparisons.userId, userId));
  }

  async createComparison(comparisonData: InsertComparison): Promise<Comparison> {
    const [comparison] = await db
      .insert(comparisons)
      .values(comparisonData)
      .returning();
    return comparison;
  }

  async updateComparison(id: string, updates: Partial<Comparison>): Promise<Comparison | undefined> {
    const [comparison] = await db
      .update(comparisons)
      .set({ ...updates, updatedAt: new Date() })
      .where(eq(comparisons.id, id))
      .returning();
    return comparison;
  }

  async deleteComparison(id: string): Promise<boolean> {
    const result = await db.delete(comparisons).where(eq(comparisons.id, id));
    return (result.rowCount ?? 0) > 0;
  }
}

export const storage = new DatabaseStorage();
