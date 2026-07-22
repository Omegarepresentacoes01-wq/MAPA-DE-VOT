import { Shield, ExternalLink } from "lucide-react";

interface Props {
  fonte: string;
  url?: string;
  limitacoes?: string;
}

export function SourceBadge({ fonte, url, limitacoes }: Props) {
  const content = (
    <span className="source-meta" title={limitacoes || fonte}>
      <Shield size={11} />
      {fonte}
      {url && <ExternalLink size={10} style={{ opacity: 0.6 }} />}
    </span>
  );
  if (url) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "none" }}>
        {content}
      </a>
    );
  }
  return content;
}
