"use client";

import { motion } from "framer-motion";
import type { StandingRow } from "@/lib/api";

function FormPill({ letter, i }: { letter: string; i: number }) {
  const cls = letter === "W" ? "form-w" : letter === "D" ? "form-d" : "form-l";
  return (
    <motion.span
      className={`form-pill ${cls}`}
      initial={{ opacity: 0, scale: 0.5 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ delay: i * 0.05 }}
    >
      {letter}
    </motion.span>
  );
}

export default function StandingsTable({ table }: { table: StandingRow[] }) {
  return (
    <div className="scroll-x">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Club</th>
            <th>P</th>
            <th>W</th>
            <th>D</th>
            <th>L</th>
            <th>GD</th>
            <th>PTS</th>
            <th>Form</th>
          </tr>
        </thead>
        <tbody>
          {table.map((row, i) => (
            <motion.tr
              key={row.team_id}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.03 }}
            >
              <td>{row.position}</td>
              <td>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <img src={row.crest} alt="" className="crest" />
                  <strong>{row.short_name}</strong>
                </div>
              </td>
              <td>{row.played}</td>
              <td>{row.won}</td>
              <td>{row.draw}</td>
              <td>{row.lost}</td>
              <td>{row.goal_difference > 0 ? `+${row.goal_difference}` : row.goal_difference}</td>
              <td>
                <strong>{row.points}</strong>
              </td>
              <td>
                <div style={{ display: "flex", gap: 4 }}>
                  {(row.form ? row.form.split(",") : []).map((l, j) => (
                    <FormPill key={j} letter={l} i={j} />
                  ))}
                </div>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
