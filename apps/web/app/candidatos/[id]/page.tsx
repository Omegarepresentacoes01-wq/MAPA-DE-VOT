import { OfficialCandidateDetail } from "@/components/candidate/OfficialCandidateDetail";

export default async function CandidatePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <OfficialCandidateDetail id={id} />;
}
