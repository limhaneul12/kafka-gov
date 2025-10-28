import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card";
import Badge from "../ui/Badge";
import Loading from "../ui/Loading";
import { consumerAPI } from "../../services/api";
import type { ConsumerMember } from "../../types";
import { Users } from "lucide-react";

interface MembersTabProps {
  groupId: string;
  clusterId: string;
}

export default function MembersTab({ groupId, clusterId }: MembersTabProps) {
  const [members, setMembers] = useState<ConsumerMember[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMembers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId, clusterId]);

  const loadMembers = async () => {
    try {
      setLoading(true);
      const response = await consumerAPI.getMembers(clusterId, groupId);
      setMembers(response.data || []);
    } catch (error) {
      console.error("Failed to load members:", error);
      toast.error("Failed to load members");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (members.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Users className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">
            No Active Members
          </h3>
          <p className="mt-2 text-sm text-gray-500">
            This consumer group has no active members
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Total Members</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {members.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Total Partitions</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {members.reduce(
                (sum, m) => sum + m.assigned_partitions.length,
                0
              )}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-600">Avg per Member</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {(
                members.reduce(
                  (sum, m) => sum + m.assigned_partitions.length,
                  0
                ) / members.length
              ).toFixed(1)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Members List */}
      <Card>
        <CardHeader>
          <CardTitle>Member Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {members.map((member, idx) => (
              <div
                key={idx}
                className="p-4 border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h4 className="font-medium text-gray-900">
                        {member.member_id}
                      </h4>
                      <Badge color="blue">
                        {member.assigned_partitions.length} partitions
                      </Badge>
                    </div>
                    <div className="mt-2 space-y-1 text-sm text-gray-600">
                      {member.client_id && (
                        <p>
                          <span className="font-medium">Client ID:</span>{" "}
                          {member.client_id}
                        </p>
                      )}
                      {member.client_host && (
                        <p>
                          <span className="font-medium">Host:</span>{" "}
                          {member.client_host}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Assigned Partitions */}
                {member.assigned_partitions.length > 0 && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      Assigned Partitions:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {member.assigned_partitions.map((partition, pidx) => (
                        <Badge key={pidx} color="gray">
                          {partition.topic}-{partition.partition}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Member Hotspot Map */}
      <Card>
        <CardHeader>
          <CardTitle>Partition Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {members.map((member, idx) => {
              const percentage =
                (member.assigned_partitions.length /
                  members.reduce(
                    (sum, m) => sum + m.assigned_partitions.length,
                    0
                  )) *
                100;
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-700 truncate max-w-xs">
                      {member.member_id}
                    </span>
                    <span className="text-gray-600">
                      {member.assigned_partitions.length} (
                      {percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        percentage > 40
                          ? "bg-rose-500"
                          : percentage > 25
                          ? "bg-yellow-500"
                          : "bg-emerald-500"
                      }`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
