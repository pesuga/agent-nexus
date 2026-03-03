"use client";

import { useEffect, useMemo, useState } from "react";
import { useAppContext } from "@/context/AppContext";
import { IconDeviceFloppy, IconCheck, IconMail, IconUser, IconAlertTriangle } from "@tabler/icons-react";

interface ProfileForm {
  displayName: string;
  email: string;
  organization: string;
  bio: string;
  avatarUrl: string;
}

export default function ProfilePage() {
  const { user, setUser } = useAppContext();
  const metaStorageKey = useMemo(
    () => `dispatch_profile_meta_${user?.actor_id || "unknown"}`,
    [user?.actor_id]
  );

  const [formData, setFormData] = useState<ProfileForm>({
    displayName: "",
    email: "",
    organization: "",
    bio: "",
    avatarUrl: "",
  });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) return;

    let localMeta: { organization?: string; bio?: string; avatarUrl?: string } = {};
    try {
      const raw = localStorage.getItem(metaStorageKey);
      if (raw) {
        localMeta = JSON.parse(raw);
      }
    } catch {
      localMeta = {};
    }

    setFormData({
      displayName: user.display_name || "",
      email: user.email || "",
      organization: localMeta.organization || "",
      bio: localMeta.bio || "",
      avatarUrl: localMeta.avatarUrl || user.avatar_url || "",
    });
  }, [user, metaStorageKey]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    setLoading(true);
    setError(null);

    let backendSaveError: string | null = null;

    try {
      const resp = await fetch(`/api/dispatch/users/${user.actor_id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ display_name: formData.displayName.trim() || null }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({ detail: "Profile save failed" }));
        backendSaveError = data.detail || "Profile save failed";
      }
    } catch {
      backendSaveError = "Profile save failed";
    }

    localStorage.setItem(
      metaStorageKey,
      JSON.stringify({
        organization: formData.organization,
        bio: formData.bio,
        avatarUrl: formData.avatarUrl,
      })
    );

    setUser({
      ...user,
      display_name: formData.displayName,
      avatar_url: formData.avatarUrl || user.avatar_url,
    });

    setSaved(true);
    setTimeout(() => setSaved(false), 3000);

    if (backendSaveError) {
      setError(`${backendSaveError}. Local profile fields were still saved in this browser.`);
    }

    setLoading(false);
  };

  return (
    <div className="container-xl py-4">
      <div className="page-header mb-4">
        <div className="row align-items-center">
          <div className="col">
            <h2 className="page-title">Profile Settings</h2>
            <div className="text-muted small mt-1">Update how your identity appears across the dashboard.</div>
          </div>
        </div>
      </div>

      <div className="row g-4">
        <div className="col-lg-4">
          <div className="card text-center py-4">
            <div className="card-body">
              <span
                className="avatar avatar-xl rounded-circle mb-3"
                style={formData.avatarUrl ? { backgroundImage: `url(${formData.avatarUrl})` } : undefined}
              >
                {!formData.avatarUrl && (formData.displayName?.charAt(0) || formData.email?.charAt(0) || "?")}
              </span>
              <h3 className="mb-1">{formData.displayName || "Unnamed User"}</h3>
              <div className="text-muted small mb-1">{formData.email || "No email"}</div>
              <div className="text-muted small">{user?.actor_role || "user"}</div>
            </div>
          </div>
        </div>

        <div className="col-lg-8">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Account Information</h3>
            </div>
            <div className="card-body">
              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label className="form-label">Display Name</label>
                  <div className="input-icon">
                    <span className="input-icon-addon"><IconUser size={18} /></span>
                    <input
                      type="text"
                      name="displayName"
                      className="form-control"
                      value={formData.displayName}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="mb-3">
                  <label className="form-label">Email Address</label>
                  <div className="input-icon">
                    <span className="input-icon-addon"><IconMail size={18} /></span>
                    <input type="email" name="email" className="form-control" value={formData.email} disabled />
                  </div>
                </div>

                <div className="mb-3">
                  <label className="form-label">Avatar URL</label>
                  <input
                    type="url"
                    name="avatarUrl"
                    className="form-control"
                    value={formData.avatarUrl}
                    onChange={handleChange}
                    placeholder="https://example.com/avatar.png"
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Organization</label>
                  <input
                    type="text"
                    name="organization"
                    className="form-control"
                    value={formData.organization}
                    onChange={handleChange}
                  />
                </div>

                <div className="mb-4">
                  <label className="form-label">Bio</label>
                  <textarea
                    name="bio"
                    className="form-control"
                    rows={4}
                    value={formData.bio}
                    onChange={handleChange}
                  ></textarea>
                </div>

                <div className="d-flex align-items-center justify-content-end border-top pt-4">
                  <button type="submit" className="btn btn-primary" disabled={loading}>
                    <IconDeviceFloppy size={18} className="me-2" />
                    {loading ? "Saving..." : "Save Changes"}
                  </button>
                </div>
              </form>

              {saved && (
                <div className="alert alert-success mt-4 mb-0" role="alert">
                  <div className="d-flex align-items-center">
                    <IconCheck size={20} className="me-2" />
                    <div>Profile saved.</div>
                  </div>
                </div>
              )}

              {error && (
                <div className="alert alert-warning mt-3 mb-0" role="alert">
                  <div className="d-flex align-items-center">
                    <IconAlertTriangle size={20} className="me-2" />
                    <div>{error}</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
