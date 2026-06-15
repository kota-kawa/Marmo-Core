-- AlterTable
ALTER TABLE "User" ADD COLUMN     "chatConsentUpdatedAt" TIMESTAMP(3),
ADD COLUMN     "chatPersistenceConsent" BOOLEAN NOT NULL DEFAULT false;
