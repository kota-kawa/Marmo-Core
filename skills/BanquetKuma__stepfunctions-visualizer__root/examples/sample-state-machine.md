# Step Functions Flow Diagram

```mermaid
graph TD
    ValidateInput[ValidateInput]
    CheckImageFormat{CheckImageFormat}
    ProcessJPEG[ProcessJPEG]
    ResizeImage[ResizeImage]
    CheckQuality{CheckQuality}
    UploadToS3[UploadToS3]
    NotifySuccess[NotifySuccess]
    ProcessingComplete[ProcessingComplete]
    LowQualityWarning[LowQualityWarning]
    ProcessingFailed[ProcessingFailed]
    ProcessPNG[ProcessPNG]
    UnsupportedFormat[UnsupportedFormat]
    ValidateInput --> CheckImageFormat
    CheckImageFormat -->|imageFormat='jpg'| ProcessJPEG
    ProcessJPEG --> ResizeImage
    ResizeImage --> CheckQuality
    CheckQuality -->|Condition 1| UploadToS3
    UploadToS3 --> NotifySuccess
    NotifySuccess --> ProcessingComplete
    CheckQuality -->|Default| LowQualityWarning
    LowQualityWarning --> UploadToS3
    ProcessJPEG -.->|Catch: States.ALL| ProcessingFailed
    CheckImageFormat -->|imageFormat='png'| ProcessPNG
    ProcessPNG --> ResizeImage
    ProcessPNG -.->|Catch: States.ALL| ProcessingFailed
    CheckImageFormat -->|Default| UnsupportedFormat
```

## Statistics

- **Total States**: 12
- **Terminal States**: 0
- **States with Error Handling**: 2

### States by Type

- **Choice**: 2
- **Fail**: 2
- **Pass**: 2
- **Succeed**: 1
- **Task**: 5