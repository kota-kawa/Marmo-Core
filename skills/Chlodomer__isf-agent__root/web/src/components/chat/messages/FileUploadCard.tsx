"use client";

import { Upload, CloudIcon } from "lucide-react";

interface FileUploadCardProps {
  onAction?: (action: string) => void;
}

export default function FileUploadCard({ onAction }: FileUploadCardProps) {
  return (
    <div className="my-3 bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="p-4">
        <h3 className="text-sm font-semibold text-gray-800 mb-2">
          Upload Past Proposals
        </h3>
        <p className="text-sm text-gray-500 mb-4 leading-relaxed">
          Share past proposals so I can learn what works and what to improve.
          You can upload successful (funded) proposals, unsuccessful (rejected)
          proposals, and reviewer feedback.
        </p>

        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-teal-400 hover:bg-teal-50/30 transition-colors cursor-pointer"
          onClick={() => onAction?.("browse-files")}
        >
          <Upload size={24} className="mx-auto mb-2 text-gray-400" />
          <p className="text-sm font-medium text-gray-600">
            Drag files here or click to browse
          </p>
          <p className="text-xs text-gray-400 mt-1">PDF, Word, or text files</p>
        </div>

        <div className="flex items-center gap-3 mt-4">
          <span className="text-xs text-gray-400">Or connect a cloud folder:</span>
          <div className="flex gap-2">
            <button
              onClick={() => onAction?.("connect-gdrive")}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
            >
              <CloudIcon size={12} />
              Google Drive
            </button>
            <button
              onClick={() => onAction?.("connect-dropbox")}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
            >
              <CloudIcon size={12} />
              Dropbox
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
