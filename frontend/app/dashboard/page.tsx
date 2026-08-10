"use client";

import { UploadForge } from "@/components/dashboard/UploadForge";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { useAuth } from "@/lib/auth-context";

export default function DashboardOverviewPage() {
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h2 className="font-display text-2xl text-parchment-100">
          Welcome back{user?.name ? `, ${user.name.split(" ")[0]}` : ""}.
        </h2>
        <p className="mt-1 text-sm text-parchment-500">
          Upload material to get started, or jump straight into a tool.
        </p>
      </div>

      <UploadForge />

      <div>
        <h3 className="mb-3 font-display text-lg text-parchment-100">Quick actions</h3>
        <QuickActions />
      </div>
    </div>
  );
}
