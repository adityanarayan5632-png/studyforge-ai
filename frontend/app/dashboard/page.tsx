"use client";

import { useEffect, useState } from "react";
import { UploadForge } from "@/components/dashboard/UploadForge";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { Card, Badge, EmptyState } from "@/components/ui/Primitives";
import { Button } from "@/components/ui/Button";
import { getDashboardSummary } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { DashboardSummary } from "@/lib/types";

export default function DashboardOverviewPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const { user, getAccessToken } = useAuth();

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const accessToken = await getAccessToken();
        const summary = await getDashboardSummary(accessToken);
        setSummary(summary);
      } catch (error) {
        console.error("Failed to load dashboard:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [getAccessToken]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-4 border-ember-500 border-t-transparent"></div>
        </div>
      </div>
    );
  }

  const displayName = summary?.profile?.display_name || user?.name;
  const firstName = displayName?.split(" ")[0];
  const gradeLabel = summary?.profile?.grade ? `Class ${summary.profile.grade}` : null;
  const boardLabel = summary?.profile?.board || null;

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h2 className="font-display text-2xl text-parchment-100">
          Welcome back{firstName ? `, ${firstName}` : ""}.
        </h2>
        <p className="mt-1 text-sm text-parchment-500">
          {gradeLabel && boardLabel ? `${gradeLabel} • ${boardLabel}` : gradeLabel || boardLabel || "Welcome to your learning dashboard"}
        </p>
      </div>

      {/* Quick Actions */}
      <div>
        <h3 className="mb-3 font-display text-lg text-parchment-100">Quick actions</h3>
        <QuickActions />
      </div>

      {/* Continue Learning */}
      {summary?.recent_conversation && (
        <div>
          <h3 className="mb-3 font-display text-lg text-parchment-100">Continue learning</h3>
          <Card className="p-5">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="font-display text-base text-parchment-100">{summary.recent_conversation.title}</h4>
                <p className="mt-1 text-sm text-parchment-500">
                  {summary.recent_conversation.message_count} messages • Updated {new Date(summary.recent_conversation.updated_at).toLocaleDateString()}
                </p>
                {summary.recent_conversation.last_message_preview && (
                  <p className="mt-2 text-sm text-parchment-400 line-clamp-2">{summary.recent_conversation.last_message_preview}</p>
                )}
              </div>
              <Button variant="ghost" size="sm">Continue</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Quiz Performance */}
      {summary && summary.quiz_performance.total_attempts > 0 && (
        <div>
          <h3 className="mb-3 font-display text-lg text-parchment-100">Quiz performance</h3>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="p-5 text-center">
              <div className="font-display text-3xl text-ember-400">{summary.quiz_performance.total_attempts}</div>
              <p className="mt-1 text-sm text-parchment-500">Quizzes completed</p>
            </Card>
            <Card className="p-5 text-center">
              <div className="font-display text-3xl text-ok-400">{summary.quiz_performance.average_score}%</div>
              <p className="mt-1 text-sm text-parchment-500">Average score</p>
            </Card>
            <Card className="p-5 text-center">
              <div className="font-display text-3xl text-ember-400">
                {summary.quiz_performance.recent_attempts[0]?.percentage || 0}%
              </div>
              <p className="mt-1 text-sm text-parchment-500">Latest score</p>
            </Card>
          </div>
        </div>
      )}

      {/* Recent Quiz Attempts */}
      {summary && summary.quiz_performance.recent_attempts.length > 0 && (
        <div>
          <h3 className="mb-3 font-display text-lg text-parchment-100">Recent quiz attempts</h3>
          <div className="space-y-3">
            {summary.quiz_performance.recent_attempts.slice(0, 5).map((attempt) => (
              <Card key={attempt.id} className="p-4 flex items-center justify-between">
                <div className="flex-1">
                  <p className="font-medium text-parchment-100">{attempt.title || "Quiz"}</p>
                  <p className="text-sm text-parchment-500">
                    {attempt.score}/{attempt.total_questions} • {attempt.percentage}% • {new Date(attempt.created_at).toLocaleDateString()}
                  </p>
                </div>
                <Badge tone={attempt.percentage >= 70 ? "ok" : attempt.percentage >= 50 ? "ember" : "err"}>
                  {attempt.percentage}%
                </Badge>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {summary && summary.recent_activities.length > 0 && (
        <div>
          <h3 className="mb-3 font-display text-lg text-parchment-100">Recent activity</h3>
          <div className="space-y-2">
            {summary.recent_activities.slice(0, 5).map((activity) => (
              <Card key={activity.id} className="p-3 flex items-center gap-3">
                <Badge tone={activity.activity_type === "quiz_completed" ? "ok" : activity.activity_type === "notes_generated" ? "ember" : "default"}>
                  {activity.activity_type.replace("_", " ")}
                </Badge>
                <p className="text-sm text-parchment-300 flex-1 truncate">
                  {activity.metadata?.source_id ? `Source: ${activity.metadata.source_id}` : ""}
                  {activity.metadata?.score !== undefined ? ` • Score: ${activity.metadata.score}/${activity.metadata.total_questions} (${activity.metadata.percentage}%)` : ""}
                </p>
                <time className="text-xs text-parchment-500">{new Date(activity.created_at).toLocaleDateString()}</time>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Recent Sources */}
      {summary && summary.recent_sources.length > 0 && (
        <div>
          <h3 className="mb-3 font-display text-lg text-parchment-100">
            Materials ({summary.source_count} total)
          </h3>
          <div className="space-y-2">
            {summary.recent_sources.slice(0, 5).map((source) => (
              <Card key={source.id} className="p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge tone="default">{source.type}</Badge>
                  <div>
                    <p className="font-medium text-parchment-100">{source.name}</p>
                    <p className="text-xs text-parchment-500">{new Date(source.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Empty State for new users */}
      {!summary?.recent_conversation && summary?.quiz_performance.total_attempts === 0 && summary?.recent_activities.length === 0 && summary?.source_count === 0 && (
        <div className="mt-8">
          <EmptyState
            title="Welcome to your dashboard"
            description="Start by uploading a PDF, YouTube video, or other material to begin learning with your AI tutor."
            action={
              <UploadForge />
            }
          />
        </div>
      )}

      {/* Upload Forge */}
      <UploadForge />

      {/* Quick Actions */}
      <div>
        <h3 className="mb-3 font-display text-lg text-parchment-100">Quick actions</h3>
        <QuickActions />
      </div>
    </div>
  );
}