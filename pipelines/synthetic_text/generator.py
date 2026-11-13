"""Synthetic text narrative generator engine for multimodal PPD screening benchmark.

Generates exactly 800 fictional English postpartum contextual narratives (640 train,
160 test) computationally linked to clinical participant IDs (BGD_001 to BGD_800).

SCIENTIFIC INTEGRITY NOTICE:
This generator produces fictional third-person contextual vignettes solely as
engineering fixtures for multimodal NLP ingestion and fusion benchmarking.
Zero authentic patient interviews, recordings, or intake notes exist in this cohort.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd

from pipelines.synthetic_text.config import (
    APPROVED_CONDITIONING_COLUMNS,
    DATA_ORIGIN_TAG,
    DEFAULT_RANDOM_SEED,
    GENERATOR_VERSION,
    LANGUAGE_CODE,
    MAX_WORD_COUNT,
    MIN_WORD_COUNT,
    MODELING_MATRIX_PATH,
    PROHIBITED_COLUMNS_EXACT,
    PROHIBITED_NARRATIVE_TERMS,
    SYNTHETIC_TEXT_DIR,
    SYNTHETIC_TEXT_MANIFEST_PATH,
    SYNTHETIC_TEXT_NARRATIVES_DIR,
    TRAIN_TEST_SPLIT_MANIFEST_PATH,
)
from pipelines.synthetic_text.templates import (
    COMMUNICATION_NEED_TEMPLATES,
    DOMESTIC_SUPPORT_TEMPLATES,
    FEEDING_TEMPLATES,
    HEALTH_ATTENTIVENESS_TEMPLATES,
    INFANT_STAGE_TEMPLATES,
    LIVING_ARRANGEMENTS,
    OCCUPATION_TEMPLATES,
    PARITY_TEMPLATES,
    SLEEP_REST_TEMPLATES,
)


class SyntheticTextGenerator:
    """Generates fictional, neutral postpartum narratives conditioned on non-target survey data."""

    def __init__(self, seed: int = DEFAULT_RANDOM_SEED) -> None:
        self.seed = seed

    def _verify_no_target_leakage(self, df: pd.DataFrame) -> None:
        """Assert that no EPDS/PHQ target, score, or prohibited clinical column enters the generator."""
        for col in df.columns:
            if col in PROHIBITED_COLUMNS_EXACT:
                raise ValueError(f"Prohibited column detected in text conditioning: '{col}'")
            col_lower = col.lower()
            if "epds" in col_lower:
                raise ValueError(f"Prohibited EPDS column detected in text conditioning: '{col}'")
            if "target" in col_lower and "partition" not in col_lower:
                raise ValueError(f"Prohibited target column detected in text conditioning: '{col}'")

    def _validate_narrative_text(self, text: str, participant_id: str) -> None:
        """Validate that generated narrative does not contain prohibited diagnostic words."""
        text_lower = text.lower()
        for term in PROHIBITED_NARRATIVE_TERMS:
            # Word boundary check
            words_in_text = set(text_lower.replace(".", " ").replace(",", " ").split())
            if term in words_in_text:
                raise ValueError(
                    f"Prohibited diagnostic term '{term}' detected in narrative for {participant_id}"
                )

    def generate_single_narrative(
        self,
        row: pd.Series,
        rng: np.random.Generator,
    ) -> Tuple[str, Dict[str, Union[int, str]]]:
        """Generate a 3-paragraph fictional narrative and metadata for a single participant.

        Args:
            row: Series containing the 13 approved non-target conditioning columns.
            rng: Deterministic participant-specific RNG.

        Returns:
            Tuple[str, Dict]: The full text narrative and metadata dictionary.
        """
        neutralized_cols: List[str] = []

        # --- THEME 1: Household Structure, Children, and Everyday Routines ---
        family_type = str(row["Family type"]).strip()
        members = str(row["Number of household members"]).strip()
        living_key = (family_type, members)
        living_options = LIVING_ARRANGEMENTS.get(
            living_key, LIVING_ARRANGEMENTS[("Nuclear", "2 to 5")]
        )
        s1 = rng.choice(living_options)

        total_children = str(row["Total children"]).strip()
        parity_options = PARITY_TEMPLATES.get(total_children, PARITY_TEMPLATES["One"])
        s2 = rng.choice(parity_options)

        occupation = str(row["Occupation After Your Latest Childbirth"]).strip()
        occ_options = OCCUPATION_TEMPLATES.get(occupation, OCCUPATION_TEMPLATES["Housewife"])
        s3 = rng.choice(occ_options)

        paragraph_1 = f"{s1} {s2} {s3}"

        # --- THEME 2: Infant Care, Feeding Routines, and Responsibilities ---
        infant_age = str(row["Age of newborn"]).strip()
        stage_options = INFANT_STAGE_TEMPLATES.get(
            infant_age, INFANT_STAGE_TEMPLATES["0 to 6 months"]
        )
        s4 = rng.choice(stage_options)

        breastfeed = str(row["Breastfeed"]).strip()
        feed_options = FEEDING_TEMPLATES.get(breastfeed, FEEDING_TEMPLATES["Yes"])
        s5 = rng.choice(feed_options)

        newborn_illness = str(row["Newborn illness"]).strip()
        worry_newborn = str(row["Worry about newborn"]).strip()
        health_key = (newborn_illness, worry_newborn)
        health_options = HEALTH_ATTENTIVENESS_TEMPLATES.get(
            health_key, HEALTH_ATTENTIVENESS_TEMPLATES[("No", "No")]
        )
        s6 = rng.choice(health_options)

        paragraph_2 = f"{s4} {s5} {s6}"

        # --- THEME 3: Sleep Windows, Rest, and Practical Family Support ---
        relax_tended = str(row["Relax/sleep when newborn is tended "]).strip()
        relax_asleep = str(row["Relax/sleep when the newborn is asleep"]).strip()
        sleep_key = (relax_tended, relax_asleep)
        sleep_options = SLEEP_REST_TEMPLATES.get(sleep_key, SLEEP_REST_TEMPLATES[("Yes", "Yes")])
        s7 = rng.choice(sleep_options)

        support_received = str(row["Recieved Support"]).strip()
        support_options = DOMESTIC_SUPPORT_TEMPLATES.get(
            support_received, DOMESTIC_SUPPORT_TEMPLATES["Medium"]
        )
        s8 = rng.choice(support_options)

        # Handling Support Need & Trust (with neutral omission for missing values)
        raw_need = row["Need for Support"]
        if pd.isna(raw_need):
            need_cat = "Missing"
            neutralized_cols.append("Need for Support")
        elif str(raw_need).strip() in ["Medium", "High"]:
            need_cat = "Elevated"
        else:
            need_cat = "Low"

        raw_trust = row["Trust and share feelings"]
        if pd.isna(raw_trust):
            trust_cat = "Missing"
            neutralized_cols.append("Trust and share feelings")
        else:
            trust_cat = str(raw_trust).strip()

        comm_key = (trust_cat, need_cat)
        comm_options = COMMUNICATION_NEED_TEMPLATES.get(
            comm_key, COMMUNICATION_NEED_TEMPLATES[("Missing", "Missing")]
        )
        s9 = rng.choice(comm_options)

        paragraph_3 = f"{s7} {s8} {s9}"

        # Combine into complete 3-paragraph narrative
        full_narrative = f"{paragraph_1}\n\n{paragraph_2}\n\n{paragraph_3}"

        word_count = len(full_narrative.split())
        char_count = len(full_narrative)
        sentence_count = 9

        meta: Dict[str, Union[int, str]] = {
            "word_count": word_count,
            "character_count": char_count,
            "sentence_count": sentence_count,
            "missing_neutralized": (
                ", ".join(neutralized_cols) if neutralized_cols else "no_missing_covariates"
            ),
        }

        return full_narrative, meta

    def generate_cohort(
        self,
        manifest_path: Union[str, Path] = TRAIN_TEST_SPLIT_MANIFEST_PATH,
        modeling_matrix_path: Union[str, Path] = MODELING_MATRIX_PATH,
        output_dir: Union[str, Path] = SYNTHETIC_TEXT_DIR,
    ) -> pd.DataFrame:
        """Generate all 800 synthetic narratives and write text_manifest.csv.

        Args:
            manifest_path: Path to frozen train_test_split_manifest.csv.
            modeling_matrix_path: Path to ppd_modeling_matrix.csv.
            output_dir: Output directory for synthetic text artifacts.

        Returns:
            pd.DataFrame: Completed text manifest.
        """
        out_dir = Path(output_dir)
        narratives_dir = out_dir / "narratives"
        narratives_dir.mkdir(parents=True, exist_ok=True)

        manifest_df = pd.read_csv(manifest_path)
        modeling_matrix_df = pd.read_csv(modeling_matrix_path)

        if len(manifest_df) != 800 or len(modeling_matrix_df) != 800:
            raise ValueError("Expected exactly 800 records in manifest and modeling matrix.")

        # Filter strictly to the approved 13 non-target columns
        safe_matrix = modeling_matrix_df[APPROVED_CONDITIONING_COLUMNS].copy()
        self._verify_no_target_leakage(safe_matrix)

        manifest_records: List[Dict[str, Union[str, int]]] = []

        for idx, split_row in manifest_df.iterrows():
            participant_id = str(split_row["participant_id"])
            sr_num = int(split_row["sr"])
            split_partition = str(split_row["split_partition"])

            # Participant-specific deterministic RNG derived from seed and participant sr
            rng_p = np.random.default_rng(self.seed * 10000 + sr_num)

            # Conditioning row
            cov_row = safe_matrix.iloc[idx]

            # Generate narrative text and metadata
            narrative_text, meta = self.generate_single_narrative(cov_row, rng_p)

            # Validate text integrity (no diagnostic words)
            self._validate_narrative_text(narrative_text, participant_id)

            # Save narrative file
            txt_filename = f"{participant_id}.txt"
            txt_rel_path = f"data/synthetic/text/narratives/{txt_filename}"
            txt_abs_path = narratives_dir / txt_filename
            with open(txt_abs_path, "w", encoding="utf-8") as f:
                f.write(narrative_text)

            # Build record dictionary
            record: Dict[str, Union[str, int]] = {
                "participant_id": participant_id,
                "split_partition": split_partition,
                "data_origin": DATA_ORIGIN_TAG,
                "generator_version": GENERATOR_VERSION,
                "random_seed": self.seed,
                "narrative_file_path": txt_rel_path,
                "word_count": meta["word_count"],
                "character_count": meta["character_count"],
                "sentence_count": meta["sentence_count"],
                "language": LANGUAGE_CODE,
                "conditioning_variables_used": ", ".join(APPROVED_CONDITIONING_COLUMNS),
                "missing_covariates_neutralized": meta["missing_neutralized"],
            }
            manifest_records.append(record)

        text_manifest_df = pd.DataFrame(manifest_records)
        manifest_save_path = out_dir / "text_manifest.csv"
        text_manifest_df.to_csv(manifest_save_path, index=False)

        return text_manifest_df


def run_generation() -> pd.DataFrame:
    """Main execution entrypoint for generating synthetic text narratives."""
    generator = SyntheticTextGenerator(seed=DEFAULT_RANDOM_SEED)
    manifest = generator.generate_cohort(
        manifest_path=TRAIN_TEST_SPLIT_MANIFEST_PATH,
        modeling_matrix_path=MODELING_MATRIX_PATH,
        output_dir=SYNTHETIC_TEXT_DIR,
    )
    print("Synthetic text generation complete.")
    print(f"  Total records: {len(manifest)}")
    print(f"  Train: {(manifest['split_partition'] == 'train').sum()}")
    print(f"  Test: {(manifest['split_partition'] == 'test').sum()}")
    print(f"  Word count min: {manifest['word_count'].min()}, max: {manifest['word_count'].max()}, mean: {manifest['word_count'].mean():.1f}")
    print(f"  Saved manifest: {SYNTHETIC_TEXT_MANIFEST_PATH}")
    print(f"  Saved narratives: {SYNTHETIC_TEXT_NARRATIVES_DIR}")
    return manifest


if __name__ == "__main__":
    run_generation()
