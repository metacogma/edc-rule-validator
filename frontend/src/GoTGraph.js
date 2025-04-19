// GoTGraph.js
// Interactive Graph of Thoughts visualization for Turing-level Validator
// Uses react, react-force-graph, and context-aware tooltips

import React, { useEffect, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";

const sampleData = {
  nodes: [
    { id: "1", label: "Validate Rule X", type: "validation" },
    { id: "2", label: "Hypothesis: Rule X is consistent", type: "hypothesis" },
    { id: "3", label: "Counterexample found", type: "counterexample" },
    { id: "4", label: "Explanation generated", type: "explanation" }
  ],
  links: [
    { source: "1", target: "2", label: "leads_to" },
    { source: "2", target: "3", label: "contradicts" },
    { source: "3", target: "4", label: "explains" }
  ]
};

function GoTGraph({ data = sampleData }) {
  const fgRef = useRef();

  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force("charge").strength(-200);
    }
  }, []);

  return (
    <div style={{ height: 500, width: "100%" }}>
      <ForceGraph2D
        ref={fgRef}
        graphData={data}
        nodeLabel={(node) => `${node.label} (${node.type})`}
        linkLabel={(link) => link.label}
        nodeAutoColorBy="type"
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.label;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.fillStyle = node.color || "#0074D9";
          ctx.beginPath();
          ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI, false);
          ctx.fill();
          ctx.fillStyle = "#222";
          ctx.fillText(label, node.x + 10, node.y + 4);
        }}
      />
    </div>
  );
}

export default GoTGraph;
