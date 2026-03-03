"use client";

import { useState, useEffect } from "react";
import { IconDeviceFloppy } from "@tabler/icons-react";
import { AgentProfile, ModelRecord } from "@/types/dispatch";

interface AgentProfileModalProps {
  profile?: AgentProfile | null;
  onClose: () => void;
  onSave: (data: Partial<AgentProfile>) => Promise<void>;
  models: ModelRecord[];
}

export default function AgentProfileModal({ profile, onClose, onSave, models }: AgentProfileModalProps) {
  const [formData, setFormData] = useState({
    name: "",
    type: "coder",
    system_prompt: "",
    model_id: "",
    provider: "openai",
    tools: [] as string[],
    skills: [] as string[],
    enabled: true,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (profile) {
      setFormData({
        name: profile.name || "",
        type: profile.type || "coder",
        system_prompt: profile.system_prompt || "",
        model_id: profile.model_id || "",
        provider: profile.provider || "openai",
        tools: profile.tools || [],
        skills: profile.skills || [],
        enabled: Boolean(profile.enabled),
      });
      return;
    }
    setFormData({
      name: "",
      type: "coder",
      system_prompt: "",
      model_id: "",
      provider: "openai",
      tools: [],
      skills: [],
      enabled: true,
    });
  }, [profile]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSave(formData);
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToolToggle = (tool: string) => {
    setFormData(prev => ({
      ...prev,
      tools: prev.tools.includes(tool) 
        ? prev.tools.filter(t => t !== tool) 
        : [...prev.tools, tool]
    }));
  };

  return (
    <div className="modal modal-blur fade show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg modal-dialog-centered">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">{profile ? "Edit Agent Profile" : "New Agent Profile"}</h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="row">
                <div className="col-lg-8">
                  <div className="mb-3">
                    <label className="form-label">Profile Name</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      value={formData.name} 
                      onChange={e => setFormData({...formData, name: e.target.value})}
                      placeholder="e.g. Senior Coder"
                      required
                    />
                  </div>
                </div>
                <div className="col-lg-4">
                  <div className="mb-3">
                    <label className="form-label">Type</label>
                    <select 
                      className="form-select"
                      value={formData.type}
                      onChange={e => setFormData({...formData, type: e.target.value})}
                    >
                      <option value="coder">Coder</option>
                      <option value="planner">Planner</option>
                      <option value="reviewer">Reviewer</option>
                      <option value="general">General</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label">System Prompt</label>
                <textarea 
                  className="form-control" 
                  rows={5}
                  value={formData.system_prompt}
                  onChange={e => setFormData({...formData, system_prompt: e.target.value})}
                  placeholder="Define the agent's personality and instructions..."
                ></textarea>
              </div>

              <div className="row">
                <div className="col-lg-6">
                  <div className="mb-3">
                    <label className="form-label">Model</label>
                    <select 
                      className="form-select"
                      value={formData.model_id}
                      onChange={e => {
                        const m = models.find(mod => mod.id === e.target.value);
                        setFormData({...formData, model_id: e.target.value, provider: m?.provider || formData.provider});
                      }}
                    >
                      <option value="">Select a model...</option>
                      {models.map(m => (
                        <option key={m.id} value={m.id}>{m.label} ({m.provider})</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="col-lg-6">
                  <div className="mb-3">
                    <label className="form-label">Status</label>
                    <label className="form-check form-switch mt-2">
                      <input 
                        className="form-check-input" 
                        type="checkbox" 
                        checked={formData.enabled}
                        onChange={e => setFormData({...formData, enabled: e.target.checked})}
                      />
                      <span className="form-check-label">Enabled</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label">Default Tools</label>
                <div className="form-selectgroup">
                  {["shell", "filesystem", "web_search", "git", "knowledge_base"].map(tool => (
                    <label key={tool} className="form-selectgroup-item">
                      <input 
                        type="checkbox" 
                        className="form-selectgroup-input" 
                        checked={formData.tools.includes(tool)}
                        onChange={() => handleToolToggle(tool)}
                      />
                      <span className="form-selectgroup-label text-capitalize">{tool.replace('_', ' ')}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-link link-secondary" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn btn-primary ms-auto" disabled={loading}>
                <IconDeviceFloppy size={18} className="me-2" />
                Save Profile
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
