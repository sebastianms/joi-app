"use client"

import { useState } from "react"
import { AlertCircle, CheckCircle2, Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

export function JSONUploadForm() {
  const [file, setFile] = useState<File | null>(null)
  const [connectionName, setConnectionName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0]
      
      // Client-side validation: size limit
      if (selectedFile.size > MAX_FILE_SIZE) {
        setError(`File is too large. Maximum allowed size is 10 MB.`)
        setFile(null)
        e.target.value = '' // reset input
        return
      }
      
      // Client-side validation: type limit (basic check)
      if (selectedFile.type !== "application/json" && !selectedFile.name.endsWith('.json')) {
        setError("Only .json files are allowed.")
        setFile(null)
        e.target.value = ''
        return
      }

      setFile(selectedFile)
      setError(null)
      setSuccess(null)
    }
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !connectionName) return

    setIsLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("name", connectionName)
      formData.append("user_session_id", "demo-session-123") // Hardcoded para MVP multitenant

      const response = await fetch("http://localhost:8000/api/connections/json", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Failed to upload JSON file")
      }

      setSuccess("JSON uploaded and validated successfully!")
      setFile(null)
      setConnectionName("")
      
      // Reseteamos el formulario HTML para borrar el input de file visualmente
      const form = e.target as HTMLFormElement
      form.reset()
      
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="space-y-4">
        
        <div className="space-y-2">
          <Label htmlFor="json-name">Connection Name</Label>
          <Input 
            id="json-name" 
            placeholder="e.g., Historical Sales Data"
            value={connectionName}
            onChange={(e) => setConnectionName(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="json-file">Upload JSON File</Label>
          <Input 
            id="json-file" 
            type="file" 
            accept=".json,application/json"
            onChange={handleFileChange}
            required
            disabled={isLoading}
            className="cursor-pointer"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Max file size: 10 MB. Format: .json
          </p>
        </div>

      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Upload Failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="border-green-500 text-green-600">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertTitle>Success</AlertTitle>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" className="w-full" disabled={isLoading || !file || !connectionName}>
        {isLoading ? "Uploading & Validating..." : (
          <>
            <Upload className="mr-2 h-4 w-4" /> Upload Data Source
          </>
        )}
      </Button>
    </form>
  )
}
