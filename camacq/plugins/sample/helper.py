"""Provide sample helpers."""


def next_well_xy(sample, plate_name, x_wells=None, y_wells=None):
    """Return the next not done well for the given plate x, y format."""
    plate = sample.get_plate(plate_name)
    if plate is None:
        return None, None
    if x_wells is None or y_wells is None:
        not_done = (
            (well_x, well_y)
            for (well_x, well_y), well in plate.wells.items()
            if not well.img_ok
        )
    else:
        done = {
            (well_x, well_y): well
            for (well_x, well_y), well in plate.wells.items()
            if well.img_ok
        }
        not_done = (
            (x_well, y_well)
            for x_well in range(x_wells)
            for y_well in range(y_wells)
            if (x_well, y_well) not in done
        )

    x_well, y_well = next(not_done, (None, None))
    return x_well, y_well
