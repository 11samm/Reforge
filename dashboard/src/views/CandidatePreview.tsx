/** Isolated review surface; loading brings the full editor viewport into view. */
export function CandidatePreview({ url, title }: { url: string; title: string }) {
  return <iframe className="candidate-review" title={title} src={url}
    sandbox="allow-scripts allow-downloads"
    onLoad={event => event.currentTarget.scrollIntoView({ block: 'center', behavior: 'auto' })} />;
}
