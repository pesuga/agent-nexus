"use client";

import { useState, useEffect } from "react";
import { useAppContext } from "@/context/AppContext";
import { IconDeviceFloppy, IconCheck, IconX } from "@tabler/icons-react";

export default function SettingsPage() {
  const { config, setConfig } = useAppContext();
  const [formData, setFormData] = useState(config);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setFormData(config);
  }, [config]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setConfig(formData);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <div className="container-tight py-4">
      <div className="card card-md">
        <div className="card-body">
          <h2 className="card-title text-center mb-4">System Settings</h2>
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">API Base URL</label>
              <input
                type="text"
                name="apiBaseUrl"
                className="form-control"
                value={formData.apiBaseUrl}
                onChange={handleChange}
                placeholder="http://localhost:8000"
              />
            </div>
            <div className="mb-3">
              <label className="form-label">Actor Role</label>
              <input
                type="text"
                name="actorRole"
                className="form-control"
                value={formData.actorRole}
                onChange={handleChange}
              />
            </div>
            <div className="mb-3">
              <label className="form-label">Actor ID</label>
              <input
                type="text"
                name="actorId"
                className="form-control"
                value={formData.actorId}
                onChange={handleChange}
              />
            </div>
            <div className="mb-3">
              <label className="form-label">API Token</label>
              <input
                type="password"
                name="apiToken"
                className="form-control"
                value={formData.apiToken}
                onChange={handleChange}
              />
            </div>
            <div className="form-footer">
              <button type="submit" className="btn btn-primary w-100">
                <IconDeviceFloppy size={18} className="me-2" />
                Save Changes
              </button>
            </div>
          </form>
          {saved && (
            <div className="alert alert-success mt-3" role="alert">
              <div className="d-flex">
                <div><IconCheck size={20} className="me-2" /></div>
                <div>Settings saved successfully!</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
