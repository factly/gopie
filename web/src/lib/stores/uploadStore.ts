import { create } from "zustand";
import { UppyFile, Meta } from "@uppy/core";
import { ValidationResult } from "@/lib/validation/validate-file";

interface UploadState {
  uploadedFile: UppyFile<Meta, Record<string, never>> | null;
  uploadResponse: unknown;
  validationResult: ValidationResult | null;
  datasetName: string;
  datasetDescription: string;
  selectedFile: File | null;
  modifiedFile: File | null;
  detectedFormat: string | null;
  originalFileName: string | null;
  
  // Actions
  setUploadedFile: (file: UppyFile<Meta, Record<string, never>> | null) => void;
  setUploadResponse: (response: unknown) => void;
  setValidationResult: (result: ValidationResult | null) => void;
  setDatasetName: (name: string) => void;
  setDatasetDescription: (description: string) => void;
  setSelectedFile: (file: File | null) => void;
  setModifiedFile: (file: File | null) => void;
  setDetectedFormat: (format: string | null) => void;
  setOriginalFileName: (name: string | null) => void;
  resetUploadState: () => void;
}

export const useUploadStore = create<UploadState>((set) => ({
  uploadedFile: null,
  uploadResponse: null,
  validationResult: null,
  datasetName: "",
  datasetDescription: "",
  selectedFile: null,
  modifiedFile: null,
  detectedFormat: null,
  originalFileName: null,
  
  setUploadedFile: (file) => set({ uploadedFile: file }),
  setUploadResponse: (response) => set({ uploadResponse: response }),
  setValidationResult: (result) => set({ validationResult: result }),
  setDatasetName: (name) => set({ datasetName: name }),
  setDatasetDescription: (description) => set({ datasetDescription: description }),
  setSelectedFile: (file) => set({ selectedFile: file }),
  setModifiedFile: (file) => set({ modifiedFile: file }),
  setDetectedFormat: (format) => set({ detectedFormat: format }),
  setOriginalFileName: (name) => set({ originalFileName: name }),
  
  resetUploadState: () => set({
    uploadedFile: null,
    uploadResponse: null,
    validationResult: null,
    datasetName: "",
    datasetDescription: "",
    selectedFile: null,
    modifiedFile: null,
    detectedFormat: null,
    originalFileName: null,
  }),
}));