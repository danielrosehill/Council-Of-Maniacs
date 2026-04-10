import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

function deAnonymizeText(text, labelToMember, members) {
  if (!labelToMember || !members) return text;

  let result = text;
  Object.entries(labelToMember).forEach(([label, memberId]) => {
    const member = members.find((m) => m.member_id === memberId);
    const displayName = member ? member.name : memberId;
    result = result.replace(new RegExp(label, 'g'), `**${displayName}**`);
  });
  return result;
}

export default function Stage2({
  rankings,
  labelToMember,
  aggregateRankings,
  stage1Results,
}) {
  const [activeTab, setActiveTab] = useState(0);

  if (!rankings || rankings.length === 0) {
    return null;
  }

  return (
    <div className="stage stage2">
      <h3 className="stage-title">Stage 2: The Maniacs Judge Each Other</h3>

      <h4>In-Character Evaluations</h4>
      <p className="stage-description">
        Each maniac evaluated all responses (anonymized as Response A, B, C,
        etc.) and ranked them — staying fully in character. Names shown in{' '}
        <strong>bold</strong> are de-anonymized for your readability.
      </p>

      <div className="tabs">
        {rankings.map((rank, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {rank.name}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="ranking-member">{rankings[activeTab].name}</div>
        <div className="ranking-content markdown-content">
          <ReactMarkdown>
            {deAnonymizeText(
              rankings[activeTab].ranking,
              labelToMember,
              stage1Results
            )}
          </ReactMarkdown>
        </div>

        {rankings[activeTab].parsed_ranking &&
          rankings[activeTab].parsed_ranking.length > 0 && (
            <div className="parsed-ranking">
              <strong>Extracted Ranking:</strong>
              <ol>
                {rankings[activeTab].parsed_ranking.map((label, i) => {
                  const memberId = labelToMember && labelToMember[label];
                  const member =
                    stage1Results &&
                    stage1Results.find((m) => m.member_id === memberId);
                  return (
                    <li key={i}>{member ? member.name : label}</li>
                  );
                })}
              </ol>
            </div>
          )}
      </div>

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <h4>Aggregate Rankings (Street Cred)</h4>
          <p className="stage-description">
            Combined results across all maniac evaluations (lower score = more
            respected by the council):
          </p>
          <div className="aggregate-list">
            {aggregateRankings.map((agg, index) => (
              <div key={index} className="aggregate-item">
                <span className="rank-position">#{index + 1}</span>
                <span className="rank-model">{agg.name}</span>
                <span className="rank-score">
                  Avg: {agg.average_rank.toFixed(2)}
                </span>
                <span className="rank-count">
                  ({agg.rankings_count} votes)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
